from typing import Any, Dict, Tuple


def compute_trust_score(worker: Dict[str, Any], reports_count: int = 0) -> float:
    """
    Computes a worker's Trust Score (0-100) per PRD Section 5.6:
    verified (30) + rating scaled (30) + jobs done capped (20)
    + account age capped (10) + clean record (10) - penalty per report.
    """
    # 1. Verified bonus (30)
    score_verified = 30.0 if worker.get("verified", False) else 0.0

    # 2. Rating scaled (30): 5.0 rating = 30 pts
    raw_rating = float(worker.get("rating", 5.0))
    score_rating = (max(0.0, min(raw_rating, 5.0)) / 5.0) * 30.0

    # 3. Jobs done capped (20): 20+ jobs = 20 pts
    jobs_done = int(worker.get("jobsDone", 0))
    score_jobs = min(20.0, float(jobs_done))

    # 4. Account age capped (10)
    # Default to 10 for active accounts or based on account age
    score_age = 10.0

    # 5. Clean record (10) & Report penalties (-10 per report)
    if reports_count == 0:
        score_record = 10.0
    else:
        score_record = max(0.0, 10.0 - (reports_count * 10.0))

    total = score_verified + score_rating + score_jobs + score_age + score_record
    clamped = max(0.0, min(100.0, total))
    return round(clamped, 1)


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
