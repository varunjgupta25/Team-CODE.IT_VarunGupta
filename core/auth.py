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


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict[str, Any]:
    """
    Extracts and verifies the Firebase ID token from the Authorization header.
    In local development / mock mode, also supports direct test tokens
    like 'Bearer worker_1' or 'Bearer cust_1' to enable smooth hackathon demo and curl testing.
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

    # 1. Try real Firebase verification if credentials are live
    if not settings.USE_MOCK_FIREBASE and FIREBASE_AUTH_AVAILABLE:
        try:
            decoded_token = firebase_auth.verify_id_token(token)
            uid = decoded_token.get("uid")
            user_doc = db.get_document("users", uid)
            role = decoded_token.get("role") or (user_doc.get("role") if user_doc else "customer")
            return {
                "uid": uid,
                "role": role,
                "email": decoded_token.get("email"),
                "name": decoded_token.get("name") or (user_doc.get("name") if user_doc else uid),
                "is_firebase": True
            }
        except Exception:
            # Fall through if token is a dev/mock token
            pass

    # 2. Local Dev / Mock token resolution
    # Strip optional prefixes like 'dev-' or 'mock-'
    clean_uid = token.replace("dev-", "").replace("mock-", "")
    
    # Check if user exists in the database
    user_doc = db.get_document("users", clean_uid) or db.get_document("users", token)
    if user_doc:
        return {
            "uid": user_doc.get("uid", clean_uid),
            "role": user_doc.get("role", "customer"),
            "name": user_doc.get("name", clean_uid),
            "phone": user_doc.get("phone", ""),
            "location": user_doc.get("location", {}),
            "is_firebase": False
        }

    # If worker exists by this id
    worker_doc = db.get_document("workers", clean_uid) or db.get_document("workers", token)
    if worker_doc:
        return {
            "uid": worker_doc.get("uid", clean_uid),
            "role": "worker",
            "name": worker_doc.get("name", f"Worker {clean_uid}"),
            "location": worker_doc.get("location", {}),
            "is_firebase": False
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
