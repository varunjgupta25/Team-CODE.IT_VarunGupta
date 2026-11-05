import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from core.database import db
from models.worker import WorkerVerifyRequest
from services.image_utils import validate_and_sanitize_image, ImageValidationError
from services.storage_provider import get_storage_provider

MAX_SUBMISSIONS_24H = 5
MAX_REJECTIONS_BEFORE_LOCK = 3


def _ensure_worker_doc(worker_id: str) -> Dict[str, Any]:
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
            "about": "Service professional in Mira Road area.",
            "rejectionCount": 0,
            "attemptCount": 0,
            "submissionHistory": []
        }
        db.set_document("workers", worker_id, worker)
    return worker


def _check_rate_limits(worker: Dict[str, Any]) -> None:
    # 1. Max rejections lock
    rejection_count = worker.get("rejectionCount", 0)
    if rejection_count >= MAX_REJECTIONS_BEFORE_LOCK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum rejection limit ({MAX_REJECTIONS_BEFORE_LOCK}) reached. An administrator must reset your attempts."
        )

    # 2. Max 5 submissions per 24 hours
    history = worker.get("submissionHistory", [])
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    valid_recent = []
    for ts_str in history:
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts > cutoff:
                valid_recent.append(ts_str)
        except Exception:
            continue

    if len(valid_recent) >= MAX_SUBMISSIONS_24H:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: maximum {MAX_SUBMISSIONS_24H} verification submissions allowed per 24 hours."
        )


def request_worker_verification(
    worker_id: str,
    req_data: WorkerVerifyRequest
) -> Dict[str, Any]:
    """Backward-compatible endpoint for non-upload metadata submission."""
    worker = _ensure_worker_doc(worker_id)
    _check_rate_limits(worker)

    doc_num = req_data.documentNumber
    masked_doc = None
    last4 = None
    if doc_num:
        clean = doc_num.strip()
        last4 = clean[-4:] if len(clean) >= 4 else clean
        masked_doc = f"•••• {last4}"

    now_iso = datetime.now(timezone.utc).isoformat()
    history = worker.get("submissionHistory", []) + [now_iso]

    updates = {
        "verificationStatus": "pending",
        "documentType": req_data.documentType or "aadhaar",
        "documentNumberMasked": masked_doc,
        "last4": last4,
        "requestedAt": now_iso,
        "submissionHistory": history,
        "attemptCount": worker.get("attemptCount", 0) + 1,
        "rejectionReason": None
    }
    db.update_document("workers", worker_id, updates)

    return {
        "status": "pending",
        "workerId": worker_id,
        "message": "Verification request submitted successfully"
    }


def submit_worker_verification_upload(
    worker_id: str,
    document_type: str,
    document_number: Optional[str],
    id_doc_bytes: bytes,
    id_doc_filename: str,
    selfie_bytes: bytes,
    selfie_filename: str
) -> Dict[str, Any]:
    """
    Submits worker ID document and live selfie for admin verification:
    - Validates magic bytes, file size, and re-encodes to strip EXIF
    - Saves to DPDP-compliant private storage
    - Enforces max 5 submissions / 24h and max 3 rejections
    - Does NOT store full document number (only last 4 digits)
    """
    worker = _ensure_worker_doc(worker_id)
    _check_rate_limits(worker)

    # Validate and sanitize ID document
    try:
        clean_id_bytes, id_ext, id_mime = validate_and_sanitize_image(id_doc_bytes, id_doc_filename)
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ID document validation failed: {str(exc)}"
        )

    # Validate and sanitize selfie
    try:
        clean_selfie_bytes, selfie_ext, selfie_mime = validate_and_sanitize_image(selfie_bytes, selfie_filename)
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Selfie image validation failed: {str(exc)}"
        )

    storage = get_storage_provider()
    id_path = f"verifications/{worker_id}/id_document.{id_ext}"
    selfie_path = f"verifications/{worker_id}/selfie.{selfie_ext}"

    storage.save_file(id_path, clean_id_bytes, id_mime)
    storage.save_file(selfie_path, clean_selfie_bytes, selfie_mime)

    last4 = None
    masked_doc = None
    if document_number:
        clean_num = document_number.replace(" ", "").replace("-", "").strip()
        last4 = clean_num[-4:] if len(clean_num) >= 4 else clean_num
        masked_doc = f"•••• {last4}"

    now_iso = datetime.now(timezone.utc).isoformat()
    history = worker.get("submissionHistory", []) + [now_iso]

    updates = {
        "verificationStatus": "pending",
        "documentType": document_type or "aadhaar",
        "documentNumberMasked": masked_doc,
        "last4": last4,
        "requestedAt": now_iso,
        "hasIdDocument": True,
        "hasSelfie": True,
        "idDocPath": id_path,
        "idDocMime": id_mime,
        "selfiePath": selfie_path,
        "selfieMime": selfie_mime,
        "submissionHistory": history,
        "attemptCount": worker.get("attemptCount", 0) + 1,
        "rejectionReason": None
    }
    db.update_document("workers", worker_id, updates)

    return {
        "status": "pending",
        "workerId": worker_id,
        "message": "Verification documents uploaded and submitted for review successfully."
    }


def get_worker_document_stream(
    worker_uid: str,
    doc_type: str,
    requester: Dict[str, Any]
) -> Tuple[bytes, str]:
    """
    Streams private verification image.
    Allowed ONLY for admin or the worker themselves.
    Returns (image_bytes, mime_type).
    """
    is_admin = requester.get("role") == "admin"
    is_self = requester.get("uid") == worker_uid

    if not (is_admin or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view documents belonging to another worker"
        )

    worker = db.get_document("workers", worker_uid)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker '{worker_uid}' not found"
        )

    if doc_type == "id_document":
        path = worker.get("idDocPath")
        mime = worker.get("idDocMime", "image/jpeg")
    elif doc_type == "selfie":
        path = worker.get("selfiePath")
        mime = worker.get("selfieMime", "image/jpeg")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type '{doc_type}'. Must be 'id_document' or 'selfie'"
        )

    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {doc_type} on file for worker '{worker_uid}'"
        )

    storage = get_storage_provider()
    content = storage.get_file(path)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document file missing from private storage"
        )

    return content, mime


def get_pending_verifications_dto() -> List[Dict[str, Any]]:
    """
    Returns a trimmed DTO for the admin pending verification queue:
    (uid, name, docType, last4, submittedAt, attemptCount, status).
    Never exposes the entire worker document or private paths.
    """
    all_workers = db.list_collection("workers")
    dtos: List[Dict[str, Any]] = []

    for w in all_workers:
        v_status = w.get("verificationStatus")
        is_verified = w.get("verified", False)
        if v_status == "pending" or (not is_verified and w.get("requestedAt")):
            last4 = w.get("last4")
            if not last4 and w.get("documentNumberMasked"):
                last4 = w["documentNumberMasked"].replace("••••", "").strip()

            dtos.append({
                "uid": w.get("uid") or w.get("id") or "",
                "name": w.get("name") or "Unknown Worker",
                "docType": w.get("documentType") or "aadhaar",
                "last4": last4,
                "submittedAt": w.get("requestedAt"),
                "attemptCount": w.get("attemptCount", 1),
                "status": v_status or "pending",
                "hasIdDocument": bool(w.get("hasIdDocument") or w.get("idDocPath")),
                "hasSelfie": bool(w.get("hasSelfie") or w.get("selfiePath")),
            })

    # Sort newest first
    dtos.sort(key=lambda x: x.get("submittedAt") or "", reverse=True)
    return dtos


def approve_worker_verification(
    worker_uid: str,
    reviewer_uid: str = "admin"
) -> Dict[str, Any]:
    """
    Approves worker verification:
    - Sets verified=True, verificationStatus=approved
    - Permanently deletes stored private document and selfie images
    - Writes immutable audit log
    """
    worker = db.get_document("workers", worker_uid)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with UID '{worker_uid}' not found"
        )

    storage = get_storage_provider()
    if worker.get("idDocPath"):
        storage.delete_file(worker["idDocPath"])
    if worker.get("selfiePath"):
        storage.delete_file(worker["selfiePath"])

    now_iso = datetime.now(timezone.utc).isoformat()

    db.update_document("workers", worker_uid, {
        "verified": True,
        "verificationStatus": "approved",
        "rejectionReason": None,
        "hasIdDocument": False,
        "hasSelfie": False,
        "idDocPath": None,
        "selfiePath": None,
        "approvedAt": now_iso
    })

    # Record audit log
    audit_id = f"v_audit_{uuid.uuid4().hex[:10]}"
    audit_doc = {
        "id": audit_id,
        "workerId": worker_uid,
        "action": "approve",
        "reviewerUid": reviewer_uid,
        "timestamp": now_iso,
        "reason": None
    }
    db.set_document("verification_audits", audit_id, audit_doc)

    return {
        "status": "approved",
        "workerId": worker_uid,
        "verified": True,
        "auditId": audit_id
    }


def reject_worker_verification(
    worker_uid: str,
    reason: str,
    reviewer_uid: str = "admin"
) -> Dict[str, Any]:
    """
    Rejects worker verification:
    - Requires a clear reason for the rejection
    - Sets verificationStatus=rejected, stores rejectionReason
    - Increments rejectionCount (locks after 3)
    - Permanently deletes stored private images
    - Writes immutable audit log
    """
    if not reason or len(reason.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid rejection reason (minimum 3 characters) is required"
        )

    worker = db.get_document("workers", worker_uid)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with UID '{worker_uid}' not found"
        )

    storage = get_storage_provider()
    if worker.get("idDocPath"):
        storage.delete_file(worker["idDocPath"])
    if worker.get("selfiePath"):
        storage.delete_file(worker["selfiePath"])

    now_iso = datetime.now(timezone.utc).isoformat()
    new_rejection_count = worker.get("rejectionCount", 0) + 1

    db.update_document("workers", worker_uid, {
        "verified": False,
        "verificationStatus": "rejected",
        "rejectionReason": reason.strip(),
        "rejectionCount": new_rejection_count,
        "hasIdDocument": False,
        "hasSelfie": False,
        "idDocPath": None,
        "selfiePath": None,
        "rejectedAt": now_iso
    })

    audit_id = f"v_audit_{uuid.uuid4().hex[:10]}"
    audit_doc = {
        "id": audit_id,
        "workerId": worker_uid,
        "action": "reject",
        "reviewerUid": reviewer_uid,
        "timestamp": now_iso,
        "reason": reason.strip()
    }
    db.set_document("verification_audits", audit_id, audit_doc)

    return {
        "status": "rejected",
        "workerId": worker_uid,
        "verified": False,
        "reason": reason.strip(),
        "rejectionCount": new_rejection_count,
        "auditId": audit_id
    }


def reset_worker_verification_attempts(
    worker_uid: str,
    reviewer_uid: str = "admin"
) -> Dict[str, Any]:
    """
    Admin resets worker rejection count so they can resubmit.
    """
    worker = db.get_document("workers", worker_uid)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker with UID '{worker_uid}' not found"
        )

    now_iso = datetime.now(timezone.utc).isoformat()

    db.update_document("workers", worker_uid, {
        "rejectionCount": 0,
        "verificationStatus": "unverified",
        "rejectionReason": None
    })

    audit_id = f"v_audit_{uuid.uuid4().hex[:10]}"
    audit_doc = {
        "id": audit_id,
        "workerId": worker_uid,
        "action": "reset_attempts",
        "reviewerUid": reviewer_uid,
        "timestamp": now_iso,
        "reason": "Admin unlocked attempts"
    }
    db.set_document("verification_audits", audit_id, audit_doc)

    return {
        "status": "reset",
        "workerId": worker_uid,
        "rejectionCount": 0
    }
