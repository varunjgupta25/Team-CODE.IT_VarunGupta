import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from main import app
from core.database import db
from services.storage_provider import get_storage_provider

client = TestClient(app)


def make_test_image(format="JPEG", size=(64, 64), color=(200, 50, 50)) -> bytes:
    out = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(out, format=format)
    return out.getvalue()


def test_worker_can_upload_valid_id_and_selfie(auth_worker_headers):
    """
    Worker can upload valid ID photo + selfie via authenticated endpoint.
    - Status changes to pending
    - Full document number is never stored (only last 4 masked)
    - Stored in private storage
    """
    id_bytes = make_test_image(format="JPEG")
    selfie_bytes = make_test_image(format="PNG")

    files = {
        "id_document": ("aadhaar_front.jpg", id_bytes, "image/jpeg"),
        "selfie": ("worker_face.png", selfie_bytes, "image/png"),
    }
    data = {
        "documentType": "aadhaar",
        "documentNumber": "987654321098"
    }

    res = client.post("/workers/verify/upload", data=data, files=files, headers=auth_worker_headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "pending"
    assert res_data["workerId"] == "worker_elec_1"

    worker = db.get_document("workers", "worker_elec_1")
    assert worker["verificationStatus"] == "pending"
    assert worker["documentType"] == "aadhaar"
    assert worker["documentNumberMasked"] == "•••• 1098"
    assert "987654321098" not in str(worker)  # Full number must NOT be in DB
    assert worker["hasIdDocument"] is True
    assert worker["hasSelfie"] is True

    # Check files exist in private storage
    storage = get_storage_provider()
    assert storage.exists(worker["idDocPath"])
    assert storage.exists(worker["selfiePath"])


def test_upload_rejects_wrong_type_and_spoofed_extension(auth_worker_headers):
    """
    Spoofed extension or non-image payload must be rejected with 400.
    """
    fake_jpg = b"This is plain text pretending to be a JPG file"
    valid_selfie = make_test_image()

    files = {
        "id_document": ("fake.jpg", fake_jpg, "image/jpeg"),
        "selfie": ("selfie.jpg", valid_selfie, "image/jpeg"),
    }
    data = {"documentType": "aadhaar", "documentNumber": "123456789012"}

    res = client.post("/workers/verify/upload", data=data, files=files, headers=auth_worker_headers)
    assert res.status_code == 400
    assert "magic bytes failed" in res.json()["detail"]


def test_upload_rejects_oversized_file(auth_worker_headers):
    """
    File exceeding 5 MB must be rejected with 400.
    """
    huge_payload = b"\xff\xd8\xff\xe0" + (b"\x00" * (5 * 1024 * 1024 + 10))
    valid_selfie = make_test_image()

    files = {
        "id_document": ("huge.jpg", huge_payload, "image/jpeg"),
        "selfie": ("selfie.jpg", valid_selfie, "image/jpeg"),
    }
    data = {"documentType": "pan", "documentNumber": "ABCDE1234F"}

    res = client.post("/workers/verify/upload", data=data, files=files, headers=auth_worker_headers)
    assert res.status_code == 400
    assert "exceeds maximum allowed size" in res.json()["detail"]


def test_upload_requires_authentication_and_worker_role(auth_customer_headers):
    """
    Unauthenticated caller gets 401; Customer role gets 403.
    """
    img = make_test_image()
    files = {
        "id_document": ("doc.jpg", img, "image/jpeg"),
        "selfie": ("selfie.jpg", img, "image/jpeg"),
    }

    # 1. Unauthenticated -> 401
    res_unauth = client.post("/workers/verify/upload", files=files)
    assert res_unauth.status_code == 401

    # 2. Customer -> 403
    res_cust = client.post("/workers/verify/upload", files=files, headers=auth_customer_headers)
    assert res_cust.status_code == 403


def test_rate_limits_max_submissions_24h(auth_worker_headers):
    """
    Max 5 submissions per worker per 24 hours. 6th submission must return 429.
    """
    img = make_test_image()

    for i in range(5):
        files = {
            "id_document": (f"doc_{i}.jpg", img, "image/jpeg"),
            "selfie": (f"selfie_{i}.jpg", img, "image/jpeg"),
        }
        res = client.post("/workers/verify/upload", files=files, headers=auth_worker_headers)
        assert res.status_code == 200, f"Submission {i+1} failed"

    # 6th submission within 24h -> 429
    files = {
        "id_document": ("doc_6.jpg", img, "image/jpeg"),
        "selfie": ("selfie_6.jpg", img, "image/jpeg"),
    }
    res_over = client.post("/workers/verify/upload", files=files, headers=auth_worker_headers)
    assert res_over.status_code == 429
    assert "Rate limit exceeded" in res_over.json()["detail"]


def test_rate_limits_max_rejections_and_admin_reset(auth_worker_headers, auth_admin_headers):
    """
    Max 3 rejections lock the account. Admin reset_attempts unlocks it.
    """
    worker_id = "worker_elec_1"
    db.update_document("workers", worker_id, {
        "rejectionCount": 3,
        "verificationStatus": "rejected"
    })

    img = make_test_image()
    files = {
        "id_document": ("doc.jpg", img, "image/jpeg"),
        "selfie": ("selfie.jpg", img, "image/jpeg"),
    }

    # Locked attempt -> 400
    res_locked = client.post("/workers/verify/upload", files=files, headers=auth_worker_headers)
    assert res_locked.status_code == 400
    assert "Maximum rejection limit" in res_locked.json()["detail"]

    # Admin resets attempts
    res_reset = client.post(f"/admin/verifications/{worker_id}/reset_attempts", headers=auth_admin_headers)
    assert res_reset.status_code == 200
    assert res_reset.json()["rejectionCount"] == 0

    # Worker can now submit again
    res_unlocked = client.post("/workers/verify/upload", files=files, headers=auth_worker_headers)
    assert res_unlocked.status_code == 200
    assert res_unlocked.json()["status"] == "pending"


def test_admin_verifications_pending_trimmed_dto(auth_worker_headers, auth_admin_headers, auth_customer_headers):
    """
    GET /admin/verifications/pending returns trimmed DTOs:
    (uid, name, docType, last4, submittedAt, attemptCount, status).
    Never exposes full worker doc. Admin-only.
    """
    # Customer gets 403
    assert client.get("/admin/verifications/pending", headers=auth_customer_headers).status_code == 403
    # Worker gets 403
    assert client.get("/admin/verifications/pending", headers=auth_worker_headers).status_code == 403

    # Worker submits verification
    img = make_test_image()
    files = {
        "id_document": ("doc.jpg", img, "image/jpeg"),
        "selfie": ("selfie.jpg", img, "image/jpeg"),
    }
    client.post("/workers/verify/upload", data={"documentType": "voter_id", "documentNumber": "XYZ9876543"}, files=files, headers=auth_worker_headers)

    # Admin calls pending endpoint
    res = client.get("/admin/verifications/pending", headers=auth_admin_headers)
    assert res.status_code == 200
    dtos = res.json()
    assert isinstance(dtos, list)
    target = next((d for d in dtos if d["uid"] == "worker_elec_1"), None)
    assert target is not None
    assert target["docType"] == "voter_id"
    assert target["last4"] == "6543"
    assert target["status"] == "pending"
    assert "rates" not in target  # Full worker doc is NOT leaked
    assert "phone" not in target
    assert "serviceRadiusKm" not in target


def test_admin_streaming_endpoint_and_privacy(auth_worker_headers, auth_worker_2_headers, auth_admin_headers):
    """
    Admin can stream document images. Worker cannot stream another worker's document (403).
    No permanent public URLs.
    """
    worker_id = "worker_elec_1"
    img = make_test_image(format="JPEG")
    files = {
        "id_document": ("doc.jpg", img, "image/jpeg"),
        "selfie": ("selfie.jpg", img, "image/jpeg"),
    }
    client.post("/workers/verify/upload", files=files, headers=auth_worker_headers)

    # Worker 2 attempts to fetch Worker 1's documents -> 403
    res_other = client.get(f"/admin/verifications/{worker_id}/documents/id_document", headers=auth_worker_2_headers)
    assert res_other.status_code == 403

    # Admin fetches Worker 1's ID document -> 200 streaming
    res_admin_id = client.get(f"/admin/verifications/{worker_id}/documents/id_document", headers=auth_admin_headers)
    assert res_admin_id.status_code == 200
    assert res_admin_id.headers["content-type"] == "image/jpeg"
    assert len(res_admin_id.content) > 0

    # Admin fetches Worker 1's selfie -> 200 streaming
    res_admin_selfie = client.get(f"/admin/verifications/{worker_id}/documents/selfie", headers=auth_admin_headers)
    assert res_admin_selfie.status_code == 200
    assert len(res_admin_selfie.content) > 0


def test_admin_approve_deletes_images_and_writes_audit(auth_worker_headers, auth_admin_headers):
    """
    Approving verification deletes images from storage and writes audit log.
    """
    worker_id = "worker_elec_1"
    img = make_test_image()
    files = {
        "id_document": ("doc.jpg", img, "image/jpeg"),
        "selfie": ("selfie.jpg", img, "image/jpeg"),
    }
    client.post("/workers/verify/upload", files=files, headers=auth_worker_headers)

    worker_before = db.get_document("workers", worker_id)
    id_path = worker_before["idDocPath"]
    selfie_path = worker_before["selfiePath"]

    storage = get_storage_provider()
    assert storage.exists(id_path)
    assert storage.exists(selfie_path)

    # Admin approves
    res = client.post(f"/admin/verifications/{worker_id}/approve", headers=auth_admin_headers)
    assert res.status_code == 200
    assert res.json()["verified"] is True

    # Images must be permanently deleted from storage
    assert not storage.exists(id_path)
    assert not storage.exists(selfie_path)

    worker_after = db.get_document("workers", worker_id)
    assert worker_after["verified"] is True
    assert worker_after["verificationStatus"] == "approved"
    assert worker_after["idDocPath"] is None
    assert worker_after["selfiePath"] is None

    # Audit record must exist in DB
    audits = db.list_collection("verification_audits")
    target_audit = next((a for a in audits if a["workerId"] == worker_id and a["action"] == "approve"), None)
    assert target_audit is not None
    assert target_audit["reviewerUid"] == "admin_user"


def test_admin_reject_requires_reason_deletes_images_and_sets_status(auth_worker_headers, auth_admin_headers):
    """
    Rejecting requires reason, deletes images, sets rejected status, writes audit log.
    """
    worker_id = "worker_elec_1"
    img = make_test_image()
    files = {
        "id_document": ("doc.jpg", img, "image/jpeg"),
        "selfie": ("selfie.jpg", img, "image/jpeg"),
    }
    client.post("/workers/verify/upload", files=files, headers=auth_worker_headers)

    worker_before = db.get_document("workers", worker_id)
    id_path = worker_before["idDocPath"]
    selfie_path = worker_before["selfiePath"]
    storage = get_storage_provider()
    assert storage.exists(id_path)

    # Missing/empty reason -> 422 or 400
    res_empty = client.post(f"/admin/verifications/{worker_id}/reject", json={"reason": "  "}, headers=auth_admin_headers)
    assert res_empty.status_code in (400, 422)

    # Valid reject
    reject_reason = "ID document text is blurry and unreadable. Please re-upload with clear lighting."
    res_rej = client.post(f"/admin/verifications/{worker_id}/reject", json={"reason": reject_reason}, headers=auth_admin_headers)
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"
    assert res_rej.json()["rejectionCount"] == 1

    # Images deleted
    assert not storage.exists(id_path)
    assert not storage.exists(selfie_path)

    # Worker record updated
    worker_after = db.get_document("workers", worker_id)
    assert worker_after["verified"] is False
    assert worker_after["verificationStatus"] == "rejected"
    assert worker_after["rejectionReason"] == reject_reason

    # Audit record exists
    audits = db.list_collection("verification_audits")
    audit = next((a for a in audits if a["workerId"] == worker_id and a["action"] == "reject"), None)
    assert audit is not None
    assert audit["reason"] == reject_reason
    assert audit["reviewerUid"] == "admin_user"

