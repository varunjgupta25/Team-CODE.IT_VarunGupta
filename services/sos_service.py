import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from core.database import db
from core.config import settings
from models.sos import SOSCreate, EmergencyContact
from services.notification_provider import get_notification_provider

RATE_LIMIT_HOURLY_SOS = 3
DUPLICATE_WINDOW_SECONDS = 60


def set_user_emergency_contact(user_id: str, contact: EmergencyContact) -> Dict[str, Any]:
    """Saves user emergency contact to both users and workers collections."""
    contact_dict = contact.model_dump()
    user_doc = db.get_document("users", user_id)
    if user_doc:
        db.update_document("users", user_id, {"emergencyContact": contact_dict})
    else:
        db.set_document("users", user_id, {"uid": user_id, "emergencyContact": contact_dict})

    worker_doc = db.get_document("workers", user_id)
    if worker_doc:
        db.update_document("workers", user_id, {"emergencyContact": contact_dict})

    return {"status": "success", "userId": user_id, "emergencyContact": contact_dict}


def get_user_emergency_contact(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves user's emergency contact if configured."""
    user_doc = db.get_document("users", user_id)
    if user_doc and user_doc.get("emergencyContact"):
        return user_doc["emergencyContact"]

    worker_doc = db.get_document("workers", user_id)
    if worker_doc and worker_doc.get("emergencyContact"):
        return worker_doc["emergencyContact"]

    return None


def _check_rate_limit_and_duplicates(
    user_id: str,
    job_id: Optional[str]
) -> Optional[Dict[str, Any]]:
    """
    Checks:
    - 60-second duplicate window for same job
    - 3 alerts per hour per user
    Returns existing record if duplicate, otherwise None.
    """
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    dup_cutoff = now - timedelta(seconds=DUPLICATE_WINDOW_SECONDS)

    all_alerts = db.list_collection("sos_alerts")
    user_recent_alerts = []

    for alert in all_alerts:
        if alert.get("userId") == user_id:
            try:
                alert_ts = datetime.fromisoformat(alert.get("createdAt"))
                if alert_ts.tzinfo is None:
                    alert_ts = alert_ts.replace(tzinfo=timezone.utc)

                # Check duplicate within 60s for same job
                if job_id and alert.get("jobId") == job_id and alert_ts > dup_cutoff:
                    return alert

                if alert_ts > one_hour_ago:
                    user_recent_alerts.append(alert)
            except Exception:
                continue

    if len(user_recent_alerts) >= RATE_LIMIT_HOURLY_SOS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: maximum {RATE_LIMIT_HOURLY_SOS} emergency SOS alerts allowed per hour."
        )

    return None


def _validate_job_participant(job_id: Optional[str], caller_uid: str) -> None:
    """Verifies that caller is either the customer or the accepted worker of the job."""
    if not job_id:
        return

    job = db.get_document("jobs", job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )

    cust_id = job.get("customerId")
    worker_id = job.get("acceptedWorkerId")

    if caller_uid != cust_id and caller_uid != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the job's customer or accepted worker can trigger an SOS alert."
        )


def _deliver_alert_with_retries(
    phone: str,
    message: str,
    channel: str = "sms",
    max_retries: int = 2
) -> Tuple[bool, Optional[str]]:
    """Attempts sending with up to 2 retries (3 total attempts)."""
    provider = get_notification_provider()
    last_err = None

    for _ in range(max_retries + 1):
        success, err = provider.send_alert(phone, message, channel=channel)
        if success:
            return True, None
        last_err = err

    return False, last_err


def trigger_sos(sos_data: SOSCreate, user_id: str) -> Dict[str, Any]:
    """
    Triggers an emergency SOS alert:
    1. Validates participant authorization (customer or accepted worker only)
    2. Validates coordinates range
    3. Returns existing record if duplicate within 60s
    4. Enforces rate limit (max 3/hour)
    5. Persists SOS record FIRST
    6. Alerts emergency contact + ops phone via NotificationProvider with retries
    7. Computes honest overall status: 'notified', 'partial', or 'failed'
    """
    job_id = sos_data.jobId
    _validate_job_participant(job_id, user_id)

    # Check duplicates and rate limit
    dup = _check_rate_limit_and_duplicates(user_id, job_id)
    if dup:
        return dup

    alert_id = f"sos_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    lat = sos_data.location.lat
    lng = sos_data.location.lng
    maps_url = f"https://www.google.com/maps?q={lat},{lng}"

    # 1. Persist the record first in the database
    doc_data = {
        "id": alert_id,
        "jobId": job_id,
        "userId": user_id,
        "location": sos_data.location.model_dump(),
        "createdAt": now_iso,
        "status": "recorded",
        "recipients": [],
        "mapsUrl": maps_url,
    }
    db.set_document("sos_alerts", alert_id, doc_data)

    # 2. Gather user info and build emergency message
    user_doc = db.get_document("users", user_id) or db.get_document("workers", user_id) or {}
    user_name = user_doc.get("name") or "RepairBuddy User"
    alert_msg = (
        f"EMERGENCY SOS ALERT: {user_name} ({user_id}) needs urgent assistance! "
        f"Job: {job_id or 'Standalone'}. "
        f"GPS: {maps_url}"
    )

    # 3. Determine recipients
    recipients_results = []
    contact = get_user_emergency_contact(user_id)

    # Recipient A: Emergency Contact (if set)
    if contact and contact.get("phone"):
        contact_phone = contact["phone"]
        success, err = _deliver_alert_with_retries(contact_phone, alert_msg)
        recipients_results.append({
            "target": "emergency_contact",
            "phone": contact_phone,
            "channel": "sms",
            "status": "sent" if success else "failed",
            "error": err
        })

    # Recipient B: Ops Alert Phone (if set)
    ops_phone = settings.OPS_ALERT_PHONE
    if ops_phone:
        success, err = _deliver_alert_with_retries(ops_phone, alert_msg)
        recipients_results.append({
            "target": "ops",
            "phone": ops_phone,
            "channel": "sms",
            "status": "sent" if success else "failed",
            "error": err
        })

    # 4. Compute overall honest status
    if not recipients_results:
        final_status = "failed"
        message = "No emergency contact or ops notification channels configured"
    else:
        sent_count = sum(1 for r in recipients_results if r["status"] == "sent")
        if sent_count == len(recipients_results):
            final_status = "notified"
            message = "All emergency contacts successfully notified"
        elif sent_count > 0:
            final_status = "partial"
            message = "Some emergency alerts failed delivery"
        else:
            final_status = "failed"
            message = "Emergency alert delivery failed to all recipients"

    doc_data["status"] = final_status
    doc_data["recipients"] = recipients_results
    doc_data["message"] = message

    db.update_document("sos_alerts", alert_id, {
        "status": final_status,
        "recipients": recipients_results,
        "message": message
    })

    return doc_data


def list_sos_alerts() -> List[Dict[str, Any]]:
    """Returns all recorded SOS alerts sorted newest first (admin-only)."""
    alerts = db.list_collection("sos_alerts")
    alerts.sort(key=lambda a: a.get("createdAt") or "", reverse=True)
    return alerts
