from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from core.database import db


def get_customer_profile(customer_id: str, requester: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves customer profile with privacy-aware masking.
    Non-owners have contact details masked.
    """
    caller_uid = requester.get("uid")
    caller_role = requester.get("role", "customer")

    user = db.get_document("users", customer_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found"
        )

    is_owner = (caller_uid == customer_id or caller_role == "admin")
    phone = user.get("phone", "")
    if not is_owner and phone:
        # Mask phone: e.g. "+91 98201 11222" -> "+91 98201 *****"
        phone = phone[:8] + "*****" if len(phone) > 8 else "****"

    return {
        "uid": user.get("uid", customer_id),
        "name": user.get("name", "Customer"),
        "role": user.get("role", "customer"),
        "phone": phone,
        "location": user.get("location", {}),
        "accountStatus": user.get("accountStatus", "ACTIVE"),
        "createdAt": user.get("createdAt")
    }


def update_customer_profile(
    customer_id: str,
    updates: Dict[str, Any],
    requester: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Updates customer profile. Only the customer themselves or an admin can update.
    """
    caller_uid = requester.get("uid")
    caller_role = requester.get("role", "customer")

    if caller_role != "admin" and caller_uid != customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this customer profile"
        )

    user = db.get_document("users", customer_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found"
        )

    allowed_fields = {"name", "phone", "location"}
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}

    if filtered_updates:
        db.update_document("users", customer_id, filtered_updates)
        user.update(filtered_updates)

    return {
        "uid": customer_id,
        "name": user.get("name"),
        "role": user.get("role", "customer"),
        "phone": user.get("phone"),
        "location": user.get("location"),
        "accountStatus": user.get("accountStatus", "ACTIVE")
    }


def get_current_user_profile(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified /users/me resolver for either customer or worker authenticated accounts.
    """
    uid = current_user.get("uid")
    user = db.get_document("users", uid)
    worker = db.get_document("workers", uid)

    if worker:
        return {
            "uid": worker.get("uid", uid),
            "role": "worker",
            "name": worker.get("name", "Worker"),
            "phone": worker.get("phone", ""),
            "skills": worker.get("skills", []),
            "rates": worker.get("rates", {}),
            "serviceRadiusKm": worker.get("serviceRadiusKm", 5.0),
            "isAvailableNow": worker.get("isAvailableNow", True),
            "verified": worker.get("verified", False),
            "rating": worker.get("rating", 5.0),
            "jobsDone": worker.get("jobsDone", 0),
            "location": worker.get("location", {}),
            "accountStatus": worker.get("accountStatus", "ACTIVE")
        }

    if user:
        return {
            "uid": user.get("uid", uid),
            "role": user.get("role", "customer"),
            "name": user.get("name", "Customer"),
            "phone": user.get("phone", ""),
            "location": user.get("location", {}),
            "accountStatus": user.get("accountStatus", "ACTIVE")
        }

    return {
        "uid": uid,
        "role": current_user.get("role", "customer"),
        "name": current_user.get("name", uid),
        "phone": current_user.get("phone", ""),
        "location": current_user.get("location", {}),
        "accountStatus": "ACTIVE"
    }
