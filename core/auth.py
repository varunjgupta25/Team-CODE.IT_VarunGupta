from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from core.config import settings
from core.database import db

# Attempt Firebase Admin Auth
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    FIREBASE_AUTH_AVAILABLE = True
except ImportError:
    FIREBASE_AUTH_AVAILABLE = False

security = HTTPBearer(auto_error=False)


def is_dev_token(token: str) -> bool:
    """
    Identifies whether a provided bearer token is a local testing / development token.
    Dev tokens include specific prefixes (token-*, dev-*, mock-*, test-*) or raw test UIDs.
    Production Firebase ID tokens are standard JWTs with two dot separators.
    """
    dev_prefixes = ("token-customer-", "token-worker-", "token-admin-", "dev-", "mock-", "test-")
    if any(token.startswith(prefix) for prefix in dev_prefixes):
        return True
    if token.startswith("cust_") or token.startswith("worker_") or token.startswith("w_") or token == "admin_user":
        return True
    # Real Firebase ID tokens are 3-part signed JWTs (header.payload.signature)
    if token.count(".") != 2:
        return True
    return False


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict[str, Any]:
    """
    Extracts and strictly verifies the Bearer token from the Authorization header.
    
    Security Guarantees:
    1. Zero 401 Fallthrough: Missing, empty, malformed, or invalid tokens fail fast with 401.
    2. Strict Environment Gating: Dev tokens are strictly forbidden when ENVIRONMENT != 'development'.
    3. No Silent Fallback: Production tokens must be cryptographically verified against Firebase Auth.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header with Bearer token"
        )

    if not credentials.scheme or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Bearer token required."
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty Bearer token provided"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Path A: Development / Mock Token Resolution (Strictly Gated)
    # ──────────────────────────────────────────────────────────────────────────
    if is_dev_token(token):
        # Strict security gate: Never permit dev/mock tokens outside development
        if settings.ENV != "development":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Dev tokens strictly prohibited in non-development environments"
            )

        clean_uid = (
            token.replace("token-customer-", "")
            .replace("token-worker-", "")
            .replace("token-admin-", "")
            .replace("dev-", "")
            .replace("mock-", "")
            .replace("test-", "")
            .strip()
        )

        id_aliases = {
            "cust_priya_1": "cust_priya",
            "w_plumb_1": "worker_plumber_1",
            "w_plumb_2": "worker_plumber_2",
            "w_plumb_3": "worker_plumber_3",
            "w_plumb_unverified": "worker_plumber_unverified",
            "w_elec_1": "worker_elec_1",
            "w_elec_2": "worker_elec_2",
            "w_elec_3": "worker_elec_3",
            "w_elec_unverified": "worker_elec_unverified",
            "w_clean_1": "worker_cleaner_1",
            "w_clean_2": "worker_cleaner_2",
            "w_clean_3": "worker_cleaner_3",
            "w_paint_1": "worker_painter_1",
            "w_maid_1": "worker_maid_1",
            "w_cook_1": "worker_cook_1",
        }
        resolved_uid = id_aliases.get(clean_uid, clean_uid)

        # Lookup in users collection
        user_doc = (
            db.get_document("users", resolved_uid)
            or db.get_document("users", clean_uid)
            or db.get_document("users", token)
        )
        if user_doc:
            return {
                "uid": user_doc.get("uid", resolved_uid),
                "role": user_doc.get("role", "customer"),
                "name": user_doc.get("name", resolved_uid),
                "phone": user_doc.get("phone", ""),
                "location": user_doc.get("location", {}),
                "is_firebase": False
            }

        # Lookup in workers collection
        worker_doc = (
            db.get_document("workers", resolved_uid)
            or db.get_document("workers", clean_uid)
            or db.get_document("workers", token)
        )
        if worker_doc:
            return {
                "uid": worker_doc.get("uid", resolved_uid),
                "role": "worker",
                "name": worker_doc.get("name", f"Worker {resolved_uid}"),
                "location": worker_doc.get("location", {}),
                "is_firebase": False
            }

        # In dev mode: allow new dev identities with standard prefixes to authenticate
        # (without writing to database, so registration endpoints can enforce duplicate checks)
        if (
            "customer" in token
            or clean_uid.startswith("cust_")
            or "worker" in token
            or clean_uid.startswith("worker_")
            or clean_uid.startswith("w_")
            or "admin" in token
            or clean_uid == "admin_user"
        ):
            role = "worker" if ("worker" in token or clean_uid.startswith("worker_") or clean_uid.startswith("w_")) else (
                "admin" if ("admin" in token or clean_uid == "admin_user") else "customer"
            )
            return {
                "uid": clean_uid,
                "role": role,
                "name": f"{role.capitalize()} {clean_uid}",
                "phone": "",
                "language": "en",
                "location": {"lat": 19.2825, "lng": 72.8570, "address": "Mira Road East, Mumbai"},
                "is_firebase": False
            }

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dev token: user not found in database"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Path B: Production Cryptographic Firebase ID Token Verification
    # ──────────────────────────────────────────────────────────────────────────
    if not FIREBASE_AUTH_AVAILABLE or not firebase_admin._apps:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is currently uninitialized or unavailable"
        )

    try:
        decoded_token = firebase_auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {exc!s}"
        ) from exc

    uid = decoded_token.get("uid") or decoded_token.get("sub")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing subject identity"
        )

    user_doc = db.get_document("users", uid)
    role = decoded_token.get("role") or (user_doc.get("role") if user_doc else "customer")

    return {
        "uid": uid,
        "role": role,
        "email": decoded_token.get("email"),
        "name": decoded_token.get("name") or (user_doc.get("name") if user_doc else uid),
        "is_firebase": True
    }


def require_role(allowed_roles: List[str]):
    """
    Enforces role-based access control (RBAC) on protected endpoints.
    """
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "customer")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{user_role}'. Required roles: {allowed_roles}"
            )
        return current_user
    return role_checker
