"""
Set Admin Custom Claims on a Firebase User.
Usage:
    python scripts/set_admin.py <firebase_uid>

Admin is NEVER self-assignable via client endpoints. This script sets the Firebase custom
claim {'admin': True, 'role': 'admin'} directly on the Firebase user profile, and updates
the database role.
"""

import argparse
import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import db

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


def init_firebase_admin():
    """Initializes Firebase Admin SDK using env vars."""
    if not FIREBASE_AVAILABLE:
        print("[ERROR] firebase-admin package is not installed.")
        sys.exit(1)

    if firebase_admin._apps:
        return

    cred = None
    if settings.FIREBASE_CREDENTIALS_JSON and settings.FIREBASE_CREDENTIALS_JSON.strip():
        try:
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
        except Exception as exc:
            print(f"[ERROR] Failed to parse FIREBASE_CREDENTIALS_JSON: {exc}")
            sys.exit(1)
    elif settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    else:
        # Check if Google Application Default Credentials can be used
        try:
            cred = credentials.ApplicationDefault()
        except Exception:
            pass

    if not cred:
        if settings.USE_MOCK_FIREBASE and settings.ENV == "development":
            print("[WARN] No Firebase credentials found. Running in local dev mock mode.")
            return
        print("[ERROR] No Firebase credentials provided. Set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH.")
        sys.exit(1)

    firebase_admin.initialize_app(cred)


def set_admin_claim(uid: str):
    """Sets custom claim {'admin': True, 'role': 'admin'} on the specified Firebase user."""
    if not uid:
        print("[ERROR] UID cannot be empty.")
        sys.exit(1)

    init_firebase_admin()

    # 1. Real Firebase Auth claim
    if firebase_admin._apps:
        try:
            # Verify user exists in Firebase Auth
            user = firebase_auth.get_user(uid)
            current_claims = user.custom_claims or {}
            current_claims.update({"admin": True, "role": "admin"})
            firebase_auth.set_custom_user_claims(uid, current_claims)
            print(f"[SUCCESS] Firebase custom claims set on UID '{uid}': {current_claims}")
        except Exception as exc:
            print(f"[ERROR] Failed to set Firebase custom claim for '{uid}': {exc}")
            sys.exit(1)

    # 2. Update database document in 'users' collection
    existing_user = db.get_document("users", uid)
    if existing_user:
        db.update_document("users", uid, {"role": "admin"})
        print(f"[SUCCESS] Updated database user '{uid}' role to 'admin'.")
    else:
        db.set_document("users", uid, {
            "uid": uid,
            "role": "admin",
            "name": "Super Admin",
        })
        print(f"[SUCCESS] Created database user '{uid}' with role 'admin'.")


def main():
    parser = argparse.ArgumentParser(description="Set Admin Custom Claim for RepairBuddy user")
    parser.add_argument("uid", nargs="?", help="Firebase User UID")
    parser.add_argument("--uid", dest="uid_flag", help="Firebase User UID flag")
    args = parser.parse_args()

    target_uid = args.uid or args.uid_flag
    if not target_uid:
        print("Usage: python scripts/set_admin.py <firebase_uid>")
        sys.exit(1)

    set_admin_claim(target_uid)


if __name__ == "__main__":
    main()

