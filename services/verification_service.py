from typing import Any, Dict
from fastapi import HTTPException, status
from core.database import db
from models.worker import WorkerVerifyRequest


from datetime import datetime, timezone

def request_worker_verification(
    worker_id: str,
    req_data: WorkerVerifyRequest
) -> Dict[str, Any]:
    worker = db.get_document("workers", worker_id)
    if not worker:
        user_doc = db.get_document("users", worker_id) or {}
        worker = {
            "uid": worker_id,
            "id": worker_id,
            "name": user_doc.get("name", "Worker"),
            "phone": user_doc.get("phone", ""),
            "skills": user_doc.get("skills", ["plumber"]),
            "rates": user_doc.get("rates", {"plumber": 350.0}),
            "isAvailableNow": True,
            "verified": False,
            "verificationStatus": "unverified",
            "rating": 4.5,
            "jobsDone": 0,
            "location": user_doc.get("location", {"lat": 19.2812, "lng": 72.8697}),
            "serviceRadiusKm": 8.0,
            "avatarUrl": "https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80",
            "about": "Service professional in Mira Road area."
        }
        db.set_document("workers", worker_id, worker)

    doc_num = req_data.documentNumber
    masked_doc = None
    if doc_num:
        clean = doc_num.strip()
        last4 = clean[-4:] if len(clean) >= 4 else clean
        masked_doc = f"•••• {last4}"

    now_iso = datetime.now(timezone.utc).isoformat()
    updates = {
        "verificationStatus": "pending",
        "documentType": req_data.documentType or "aadhaar",
        "documentNumberMasked": masked_doc,
        "requestedAt": now_iso
    }
    db.update_document("workers", worker_id, updates)

    return {
        "status": "pending",
        "workerId": worker_id,
        "message": "Verification request submitted successfully"
    }


def approve_worker_verification(
    worker_uid: str
) -> Dict[str, Any]:
    worker = db.get_document("workers", worker_uid)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with UID '{worker_uid}' not found"
        )

    db.update_document("workers", worker_uid, {
        "verified": True,
        "verificationStatus": "approved"
    })

    return {
        "status": "approved",
        "workerId": worker_uid,
        "verified": True
    }
