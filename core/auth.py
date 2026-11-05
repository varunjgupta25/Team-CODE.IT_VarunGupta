from typing import Any, Dict, Optional
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


def _verify_firebase_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Firebase ID token using firebase-admin SDK.
    Admin privileges require an explicit custom claim ('admin': True or 'role': 'admin').
    """
    if not FIREBASE_AUTH_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase authentication is not available"
        )

    try:
        decoded_token = firebase_auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(exc)}"
        )

    uid = decoded_token.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid"
        )

    # Check for admin custom claim set via scripts/set_admin.py
    is_admin = decoded_token.get("admin") is True or decoded_token.get("role") == "admin"
    user_doc = db.get_document("users", uid)

    if is_admin:
        role = "admin"
    else:
        # Fallback to role stored in users doc, but never allow admin without the custom claim
        role = user_doc.get("role") if user_doc else "customer"
        if role == "admin":
            role = "customer"

    return {
        "uid": uid,
        "role": role,
        "email": decoded_token.get("email"),
        "phone": decoded_token.get("phone_number") or (user_doc.get("phone") if user_doc else ""),
        "name": decoded_token.get("name") or (user_doc.get("name") if user_doc else uid),
        "is_firebase": True,
    }


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict[str, Any]:
    """
    Extracts and verifies the Bearer token from the Authorization header.
    In production (or anytime ENV!=development or USE_MOCK_FIREBASE=false), strictly requires
    a valid, non-expired Firebase ID token.
    Dev convenience (seeded direct UIDs) is ONLY permitted when ENV=development AND USE_MOCK_FIREBASE=true.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header with Bearer token"
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty Bearer token provided"
        )

    # Determine if dev convenience is permitted
    dev_mode_allowed = (settings.ENV == "development" and settings.USE_MOCK_FIREBASE)

    # In production / non-dev config, strictly verify with Firebase. No fallthrough.
    if not dev_mode_allowed:
        return _verify_firebase_token(token)

    # When in dev mode (ENV=development AND USE_MOCK_FIREBASE=true):
    # Try Firebase verification first if firebase is initialized and token is a JWT
    if FIREBASE_AUTH_AVAILABLE and getattr(firebase_admin, "_apps", None):
        try:
            return _verify_firebase_token(token)
        except HTTPException:
            # Fall through to dev convenience for direct mock user IDs only in development
            pass

    # Dev token resolution: direct lookup of seeded/mock UIDs in database
    user_doc = db.get_document("users", token)
    if user_doc:
        return {
            "uid": user_doc.get("uid", token),
            "role": user_doc.get("role", "customer"),
            "name": user_doc.get("name", token),
            "phone": user_doc.get("phone", ""),
            "location": user_doc.get("location", {}),
            "is_firebase": False,
        }

    worker_doc = db.get_document("workers", token)
    if worker_doc:
        return {
            "uid": worker_doc.get("uid", token),
            "role": "worker",
            "name": worker_doc.get("name", f"Worker {token}"),
            "phone": worker_doc.get("phone", ""),
            "location": worker_doc.get("location", {}),
            "is_firebase": False,
        }

    # Token not found in database and not verified by Firebase
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token: user not found"
    )


def require_role(allowed_roles: list[str]):
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "customer")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{user_role}'. Required roles: {allowed_roles}"
            )
        return current_user
    return role_checker
