"""
tests/test_trust_engine.py - Unit tests for Bayesian rating engine,
account age weighting, composite trust score, and abuse auto-flagging.
"""
import pytest
from datetime import datetime, timezone, timedelta

from services.trust_engine import (
    calculate_bayesian_rating,
    compute_account_age_days,
    compute_account_age_multiplier,
    compute_trust_score,
    compute_trust_badge,
    get_worker_trust_info,
    evaluate_abuse_threshold,
    parse_iso_utc,
    DEFAULT_GLOBAL_MEAN_RATING,
    DEFAULT_MIN_REVIEWS_WEIGHT,
    MIN_AGE_MULTIPLIER,
    UNDER_REVIEW_STATUS,
)


# ---------------------------------------------------------------------------
# 1. calculate_bayesian_rating
# ---------------------------------------------------------------------------

class TestBayesianRating:
    def test_zero_reviews_returns_global_mean(self):
        """With no reviews, Bayesian rating should equal the global mean."""
        result = calculate_bayesian_rating(0, 0.0)
        assert result == DEFAULT_GLOBAL_MEAN_RATING

    def test_one_review_biased_toward_mean(self):
        """One 5-star review should be pulled toward global mean (~4.58)."""
        result = calculate_bayesian_rating(1, 5.0)
        # (1*5 + 5*4.5) / (1+5) = (5 + 22.5) / 6 = 27.5/6 ≈ 4.58
        assert 4.5 < result < 5.0
        assert result == round(27.5 / 6.0, 2)

    def test_high_review_count_true_average_dominates(self):
        """With 100 reviews, Bayesian output should approach true average."""
        result = calculate_bayesian_rating(100, 4.9)
        # (100*4.9 + 5*4.5) / 105 = (490 + 22.5) / 105 ≈ 4.88
        expected = round((100 * 4.9 + 5 * 4.5) / 105, 2)
        assert result == expected

    def test_negative_review_count_clamps_to_zero(self):
        """Negative review counts should be treated as zero."""
        result = calculate_bayesian_rating(-5, 3.0)
        assert result == DEFAULT_GLOBAL_MEAN_RATING

    def test_extreme_low_rating_clamps(self):
        """Rating below 1.0 should be clamped to 1.0."""
        result = calculate_bayesian_rating(10, 0.0)
        # v=10, R clamped to 1.0: (10*1 + 5*4.5) / 15 = 32.5/15 ≈ 2.17
        expected = round((10 * 1.0 + 5 * 4.5) / 15, 2)
        assert result == expected

    def test_extreme_high_rating_clamps(self):
        """Rating above 5.0 should be clamped to 5.0."""
        result = calculate_bayesian_rating(10, 9.0)
        expected = round((10 * 5.0 + 5 * 4.5) / 15, 2)
        assert result == expected

    def test_result_always_between_1_and_5(self):
        """Output should always stay in [1.0, 5.0]."""
        for v in [0, 1, 5, 50, 1000]:
            for r in [0.0, 1.0, 2.5, 4.0, 5.0, 10.0]:
                result = calculate_bayesian_rating(v, r)
                assert 1.0 <= result <= 5.0


# ---------------------------------------------------------------------------
# 2. Account Age Functions
# ---------------------------------------------------------------------------

class TestAccountAge:
    def test_missing_created_at_returns_zero(self):
        assert compute_account_age_days(None) == 0.0
        assert compute_account_age_days("") == 0.0

    def test_future_timestamp_returns_zero(self):
        future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        assert compute_account_age_days(future) == 0.0

    def test_valid_past_timestamp(self):
        now = datetime.now(timezone.utc)
        ten_days_ago = (now - timedelta(days=10)).isoformat()
        age = compute_account_age_days(ten_days_ago, now_utc=now)
        assert 9.9 < age < 10.1

    def test_z_suffix_parsed_correctly(self):
        now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        created = "2026-06-10T12:00:00Z"
        age = compute_account_age_days(created, now_utc=now)
        assert 4.9 < age < 5.1


class TestAccountAgeMultiplier:
    def test_brand_new_account_gets_min_multiplier(self):
        now = datetime.now(timezone.utc)
        created = now.isoformat()
        m = compute_account_age_multiplier(created, now_utc=now)
        assert m == MIN_AGE_MULTIPLIER  # 0.70

    def test_seven_day_old_account(self):
        now = datetime.now(timezone.utc)
        created = (now - timedelta(days=7)).isoformat()
        m = compute_account_age_multiplier(created, now_utc=now)
        # progress = 7/30, multiplier = 0.7 + 0.3*(7/30) ≈ 0.77
        assert 0.76 < m < 0.78

    def test_thirty_day_old_account_is_mature(self):
        now = datetime.now(timezone.utc)
        created = (now - timedelta(days=30)).isoformat()
        m = compute_account_age_multiplier(created, now_utc=now)
        assert m == 1.0

    def test_ninety_day_old_account_is_mature(self):
        now = datetime.now(timezone.utc)
        created = (now - timedelta(days=90)).isoformat()
        m = compute_account_age_multiplier(created, now_utc=now)
        assert m == 1.0

    def test_none_created_at_gets_min_multiplier(self):
        m = compute_account_age_multiplier(None)
        assert m == MIN_AGE_MULTIPLIER


# ---------------------------------------------------------------------------
# 3. Composite Trust Score
# ---------------------------------------------------------------------------

class TestTrustScore:
    def test_verified_worker_with_good_stats(self):
        worker = {
            "verified": True,
            "rating": 4.8,
            "jobsDone": 15,
            "createdAt": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
        }
        score = compute_trust_score(worker, reports_count=0)
        # 30 verified + ~28.8 rating + 15 jobs + 10 age + 10 clean ≈ 93+
        assert score >= 80.0

    def test_unverified_new_worker(self):
        now = datetime.now(timezone.utc)
        worker = {
            "verified": False,
            "rating": 5.0,
            "jobsDone": 0,
            "createdAt": now.isoformat(),
        }
        score = compute_trust_score(worker, reports_count=0)
        # 0 verified + ~27 rating (bayesian pulls down) + 0 jobs + 7 age + 10 clean ≈ 44
        assert score < 60.0

    def test_reports_reduce_score(self):
        worker = {
            "verified": True,
            "rating": 4.5,
            "jobsDone": 10,
            "createdAt": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
        }
        clean = compute_trust_score(worker, reports_count=0)
        reported = compute_trust_score(worker, reports_count=2)
        assert reported < clean

    def test_score_clamped_to_0_100(self):
        worker = {"verified": False, "rating": 1.0, "jobsDone": 0}
        score = compute_trust_score(worker, reports_count=5)
        assert 0.0 <= score <= 100.0


class TestTrustBadge:
    def test_gold_badge(self):
        assert compute_trust_badge(85.0) == "Gold"

    def test_silver_badge(self):
        assert compute_trust_badge(65.0) == "Silver"

    def test_bronze_badge(self):
        assert compute_trust_badge(45.0) == "Bronze"

    def test_new_badge(self):
        assert compute_trust_badge(20.0) == "New"

    def test_get_worker_trust_info_returns_tuple(self):
        worker = {"verified": True, "rating": 4.0, "jobsDone": 25,
                  "createdAt": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()}
        score, badge = get_worker_trust_info(worker)
        assert isinstance(score, float)
        assert badge in ("Gold", "Silver", "Bronze", "New")


# ---------------------------------------------------------------------------
# 4. Abuse Threshold Evaluation
# ---------------------------------------------------------------------------

class TestAbuseThreshold:
    def _make_report(self, status_val="pending", hours_ago=1):
        ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
        return {"status": status_val, "createdAt": ts}

    def test_three_pending_reports_in_window_triggers(self):
        reports = [self._make_report("pending", h) for h in [1, 2, 3]]
        assert evaluate_abuse_threshold(reports) is True

    def test_two_pending_reports_does_not_trigger(self):
        reports = [self._make_report("pending", h) for h in [1, 2]]
        assert evaluate_abuse_threshold(reports) is False

    def test_dismissed_reports_excluded(self):
        reports = [
            self._make_report("pending", 1),
            self._make_report("dismissed", 2),
            self._make_report("resolved", 3),
            self._make_report("pending", 4),
        ]
        # Only 2 pending, should not trigger
        assert evaluate_abuse_threshold(reports) is False

    def test_old_reports_excluded(self):
        reports = [
            self._make_report("pending", 1),
            self._make_report("pending", 2),
            self._make_report("pending", 72),  # 72 hours ago, outside 48h window
        ]
        assert evaluate_abuse_threshold(reports) is False

    def test_empty_reports_does_not_trigger(self):
        assert evaluate_abuse_threshold([]) is False

    def test_exactly_threshold_triggers(self):
        reports = [self._make_report("pending", h) for h in [10, 20, 30]]
        assert evaluate_abuse_threshold(reports) is True

    def test_mixed_statuses_and_ages(self):
        reports = [
            self._make_report("pending", 1),
            self._make_report("pending", 5),
            self._make_report("rejected", 2),
            self._make_report("pending", 47),  # still inside 48h window
        ]
        # 3 pending within window → triggers
        assert evaluate_abuse_threshold(reports) is True


# ---------------------------------------------------------------------------
# 5. Integration: Report endpoint auto-flags worker
# ---------------------------------------------------------------------------

class TestReportAutoFlagIntegration:
    """Integration tests using FastAPI TestClient to verify that submitting
    3 reports via POST /reports auto-flags the worker with UNDER_REVIEW."""

    @pytest.fixture(autouse=True)
    def setup(self, isolated_db):
        """Uses the isolated_db fixture from conftest."""
        from core.database import db
        self.db = db

        # Seed a worker
        self.worker_id = "worker_trust_test_001"
        self.db.set_document("workers", self.worker_id, {
            "id": self.worker_id,
            "uid": "uid_trust_worker",
            "displayName": "Trust Test Worker",
            "skills": ["plumbing"],
            "verified": True,
            "rating": 4.5,
            "jobsDone": 10,
            "isFlagged": False,
            "flagged": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })

        # Seed reporter user — using cust_ prefix so dev token resolver maps it correctly
        self.reporter_uid = "cust_reporter_trust"
        self.db.set_document("users", self.reporter_uid, {
            "uid": self.reporter_uid,
            "displayName": "Reporter User",
            "role": "customer",
        })

    def _auth_header(self):
        """Use a standard dev token that resolves to the seeded reporter user."""
        return {"Authorization": f"Bearer {self.reporter_uid}"}

    def test_three_reports_auto_flags_worker(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        headers = self._auth_header()

        # Submit 3 reports
        for i in range(3):
            resp = client.post("/reports", json={
                "workerId": self.worker_id,
                "reason": f"Test report #{i+1}",
                "category": "spam",
            }, headers=headers)
            assert resp.status_code in (200, 201), f"Report {i+1} failed: {resp.text}"

        # Check worker is now flagged
        worker = self.db.get_document("workers", self.worker_id)
        assert worker["isFlagged"] is True
        assert worker["flagged"] is True
        assert worker.get("accountStatus") == UNDER_REVIEW_STATUS

    def test_two_reports_does_not_flag(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        headers = self._auth_header()

        # Submit only 2 reports
        for i in range(2):
            resp = client.post("/reports", json={
                "workerId": self.worker_id,
                "reason": f"Test report #{i+1}",
                "category": "harassment",
            }, headers=headers)
            assert resp.status_code in (200, 201)

        worker = self.db.get_document("workers", self.worker_id)
        assert worker.get("isFlagged", False) is False
        assert worker.get("accountStatus") != UNDER_REVIEW_STATUS

    def test_report_includes_category_field(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        headers = self._auth_header()

        resp = client.post("/reports", json={
            "workerId": self.worker_id,
            "reason": "Category test",
            "category": "no_show",
        }, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["category"] == "no_show"

    def test_invalid_category_defaults_to_other(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        headers = self._auth_header()

        resp = client.post("/reports", json={
            "workerId": self.worker_id,
            "reason": "Invalid category test",
            "category": "BOGUS_CATEGORY",
        }, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["category"] == "other"

    def test_flagged_worker_demoted_from_feed(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        headers = self._auth_header()

        # Submit 3 reports to auto-flag worker
        for i in range(3):
            client.post("/reports", json={
                "workerId": self.worker_id,
                "reason": f"Spam #{i+1}",
                "category": "spam",
            }, headers=headers)

        # Worker feed should not contain this worker
        feed_resp = client.get("/workers/feed", headers=headers)
        assert feed_resp.status_code == 200
        feed_ids = [w.get("id") for w in feed_resp.json()]
        assert self.worker_id not in feed_ids
