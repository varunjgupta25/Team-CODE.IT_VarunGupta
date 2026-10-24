import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from core.database import db
from models.sos import SOSCreate


def trigger_sos(sos_data: SOSCreate, user_id: str) -> Dict[str, Any]:
    alert_id = f"sos_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_data = {
        "id": alert_id,
        "jobId": sos_data.jobId,
        "userId": user_id,
        "location": sos_data.location.model_dump(),
        "createdAt": now_iso,
        "status": "recorded"
    }

    db.set_document("sos_alerts", alert_id, doc_data)
    return doc_data
