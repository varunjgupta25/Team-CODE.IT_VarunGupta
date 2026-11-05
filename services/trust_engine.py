"""
services/trust_engine.py - Bayesian Rating & Trust Score Engine, Account Age Factor,
and Abuse Reporting Rules Module.

Mathematical Formulations:
1. Bayesian Weighted Rating:
     Weighted Rating = ((v * R) + (m * C)) / (v + m)
   Where:
     v = total number of reviews for the worker.
     R = average review rating of the worker.
     m = minimum review threshold weight (default 5.0).
     C = global mean rating across all platform workers (default 4.5).

2. Account Age Factor Weighting:
     Dynamic account age in days computed from created_at in UTC.
     Accounts under minimum threshold receive a calibrated age-trust modifier,
     escalating to 1.0 as the account matures (>= 30 days).

3. Abuse Reporting & Auto-Flagging Rules:
     If unreviewed/pending reports for an entity meet or exceed the threshold
     (default: >= 3 reports in 48 hours), the account status is updated to
     UNDER_REVIEW and is demoted from matching feeds.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Bayesian constants
DEFAULT_GLOBAL_MEAN_RATING: float = 4.5  # C
DEFAULT_MIN_REVIEWS_WEIGHT: float = 5.0  # m

# Account age constants
MIN_AGE_THRESHOLD_DAYS: float = 7.0
MATURE_ACCOUNT_DAYS: float = 30.0
MIN_AGE_MULTIPLIER: float = 0.70

# Abuse rule constants
AUTO_FLAG_THRESHOLD: int = 3
AUTO_FLAG_WINDOW_HOURS: int = 48
UNDER_REVIEW_STATUS: str = "UNDER_REVIEW"

VALID_REPORT_CATEGORIES: List[str] = [
    "spam", "harassment", "no_show", "fraud", "unprofessional", "safety", "other"
]


# ---------------------------------------------------------------------------
# 1. Bayesian Rating Calculation Engine
# ---------------------------------------------------------------------------

def calculate_bayesian_rating(
    review_count: int,
    average_rating: float,
    min_weight: float = DEFAULT_MIN_REVIEWS_WEIGHT,
    global_mean: float = DEFAULT_GLOBAL_MEAN_RATING
) -> float:
    """
    Computes a Bayesian weighted rating to prevent bias on accounts with very few reviews.

    Formula:
      Weighted Rating = ((v * R) + (m * C)) / (v + m)

    Edge Cases:
    - v = 0: returns global_mean (e.g. 4.5)
    - v = 1, R = 5.0: weighted toward global_mean (~4.58)
    - v = 100, R = 4.9: true average dominates (~4.88)
    """
    v = max(0, int(review_count))
    m = max(0.1, float(min_weight))
    C = max(1.0, min(5.0, float(global_mean)))

    if v == 0:
        return round(C, 2)

    R = max(1.0, min(5.0, float(average_rating)))
    weighted = ((v * R) + (m * C)) / (v + m)
    return round(max(1.0, min(5.0, weighted)), 2)


# ---------------------------------------------------------------------------
# 2. Account Age Factor Weighting
# ---------------------------------------------------------------------------

def parse_iso_utc(timestamp_str: str) -> datetime:
    """
    Parses ISO 8601 string into timezone-aware UTC datetime.
    Handles 'Z', trailing offsets, and naive formats safely.
    """
    ts = timestamp_str.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        # Fallback for common standard formats
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(ts, fmt)
                break
            except ValueError:
                continue
        else:
            dt = datetime.now(timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_account_age_days(
    created_at: Optional[str],
    now_utc: Optional[datetime] = None
) -> float:
    """
    Computes dynamic account age in days from created_at in UTC.
    Returns 0.0 if created_at is missing or in the future.
    """
    if not created_at:
        return 0.0

    now = now_utc or datetime.now(timezone.utc)
    try:
        created_dt = parse_iso_utc(created_at)
        delta_seconds = (now - created_dt).total_seconds()
        return max(0.0, round(delta_seconds / 86400.0, 3))
    except Exception:
        return 0.0


def compute_account_age_multiplier(
    created_at: Optional[str],
    min_threshold_days: float = MIN_AGE_THRESHOLD_DAYS,
    mature_days: float = MATURE_ACCOUNT_DAYS,
    min_multiplier: float = MIN_AGE_MULTIPLIER,
    now_utc: Optional[datetime] = None
) -> float:
    """
    Applies trust multiplier curve based on dynamic account age:
    - Accounts >= mature_days (30 days): 1.0 multiplier
    - Accounts < min_threshold_days (7 days): receive calibrated modifier starting at min_multiplier
    - Monotonically scales between min_multiplier and 1.0.
    """
    age_days = compute_account_age_days(created_at, now_utc=now_utc)
    if age_days >= mature_days:
        return 1.0

    progress = age_days / mature_days
    multiplier = min_multiplier + (1.0 - min_multiplier) * progress
    return round(max(min_multiplier, min(1.0, multiplier)), 3)


# ---------------------------------------------------------------------------
# 3. Composite Trust Score & Badge Engine
# ---------------------------------------------------------------------------

def compute_trust_score(worker: Dict[str, Any], reports_count: int = 0) -> float:
    """
    Computes a worker's Trust Score (0-100) integrated with Bayesian rating
    and account age modifier:
      Verified bonus (30) + Bayesian rating scaled (30) + jobs done (20)
      + Account age factor (10) + Clean record (10) - Report penalties.
    """
    # 1. Verified bonus (30 pts)
    score_verified = 30.0 if worker.get("verified", False) else 0.0

    # 2. Bayesian weighted rating scaled to 30 pts
    raw_rating = float(worker.get("rating", 5.0))
    review_count = int(worker.get("reviewCount") or worker.get("review_count") or worker.get("jobsDone", 0))
    weighted_rating = calculate_bayesian_rating(review_count, raw_rating)
    score_rating = (weighted_rating / 5.0) * 30.0

    # 3. Jobs done capped at 20 pts
    jobs_done = int(worker.get("jobsDone", 0))
    score_jobs = min(20.0, float(jobs_done))

    # 4. Account age component (up to 10 pts scaled by age multiplier)
    created_at = worker.get("createdAt") or worker.get("created_at")
    age_multiplier = compute_account_age_multiplier(created_at)
    score_age = 10.0 * age_multiplier

    # 5. Clean record (10 pts) and report penalty (-10 pts per report)
    if reports_count == 0:
        score_record = 10.0
    else:
        score_record = max(0.0, 10.0 - (reports_count * 10.0))

    total = score_verified + score_rating + score_jobs + score_age + score_record
    return round(max(0.0, min(100.0, total)), 1)


def compute_trust_badge(trust_score: float) -> str:
    """
    Maps 0-100 Trust Score into tier badge.
    """
    if trust_score >= 80.0:
        return "Gold"
    elif trust_score >= 60.0:
        return "Silver"
    elif trust_score >= 40.0:
        return "Bronze"
    return "New"


def get_worker_trust_info(worker: Dict[str, Any], reports_count: int = 0) -> Tuple[float, str]:
    score = compute_trust_score(worker, reports_count)
    badge = compute_trust_badge(score)
    return score, badge


# ---------------------------------------------------------------------------
# 4. Abuse Reporting & Auto-Flagging Rules Engine
# ---------------------------------------------------------------------------

def evaluate_abuse_threshold(
    reports: List[Dict[str, Any]],
    threshold: int = AUTO_FLAG_THRESHOLD,
    window_hours: int = AUTO_FLAG_WINDOW_HOURS,
    now_utc: Optional[datetime] = None
) -> bool:
    """
    Evaluates whether unreviewed abuse reports meet or exceed the threshold
    within the rolling time window (default 3 reports within 48 hours).
    """
    now = now_utc or datetime.now(timezone.utc)
    active_recent_reports = 0

    for r in reports:
        # Ignore already dismissed / resolved reports
        if r.get("status") in ["dismissed", "resolved", "rejected"]:
            continue

        created_str = r.get("createdAt") or r.get("created_at")
        if created_str:
            try:
                r_dt = parse_iso_utc(created_str)
                age_hours = (now - r_dt).total_seconds() / 3600.0
                if age_hours <= window_hours:
                    active_recent_reports += 1
            except Exception:
                active_recent_reports += 1
        else:
            active_recent_reports += 1

    return active_recent_reports >= threshold

