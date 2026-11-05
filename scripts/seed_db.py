"""
scripts/seed_db.py

Production-grade database migration and seeding utility.
Connects directly to the configured Firestore instance (remote production or local development)
and populates initial lookup schemas, system configurations, and seed entities.

Usage:
    python scripts/seed_db.py [--clean] [--remote] [--verify]

Options:
    --clean     Wipes existing collections before inserting seed data.
    --remote    Enforces connection to remote Firestore (fails if in mock mode).
    --verify    Checks database connectivity and collection counts after seeding.
"""

import argparse
from datetime import datetime, timezone
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import db

# Required service categories
SERVICE_CATEGORIES = [
    {"id": "electrician", "name": "Electrician", "base_rate": 400.0, "active": True},
    {"id": "plumber", "name": "Plumber", "base_rate": 350.0, "active": True},
    {"id": "carpenter", "name": "Carpenter", "base_rate": 450.0, "active": True},
    {"id": "painter", "name": "Painter", "base_rate": 500.0, "active": True},
    {"id": "appliance_repair", "name": "Appliance Repair", "base_rate": 450.0, "active": True},
    {"id": "cleaner", "name": "House Cleaner", "base_rate": 300.0, "active": True},
    {"id": "cook", "name": "Home Cook", "base_rate": 400.0, "active": True},
]


def seed_database(clean: bool = False, require_remote: bool = False, verify: bool = True):
    print("=" * 70)
    print(" RepairBuddy Database Migration & Seed Tool")
    print("=" * 70)

    # 1. Connect & Validate
    db.connect()
    is_mock = getattr(db, "_use_mock", True)
    mode_str = "MOCK (in-memory)" if is_mock else "REMOTE FIRESTORE (Production)"
    print(f"[*] Target Database Backend: {mode_str}")

    if require_remote and is_mock:
        raise RuntimeError("CRITICAL: --remote was specified but database is operating in mock mode.")

    now_iso = datetime.now(timezone.utc).isoformat()

    # 2. Clean if requested
    collections = ["categories", "system_config", "users", "workers", "jobs", "offers", "reviews", "sos_alerts", "reports"]
    if clean:
        print("[*] Cleaning existing collections...")
        for col in collections:
            db.clear_collection(col)
        print("[+] Collections cleared successfully.")

    # 3. Seed Service Categories (Lookup data)
    print("[*] Seeding service categories...")
    for cat in SERVICE_CATEGORIES:
        cat_data = dict(cat)
        cat_data["created_at"] = now_iso
        cat_data["updated_at"] = now_iso
        db.set_document("categories", cat["id"], cat_data)
    print(f"[+] Seeded {len(SERVICE_CATEGORIES)} service categories.")

    # 4. Seed System Configuration
    print("[*] Seeding system configuration...")
    sys_config = {
        "project_name": settings.PROJECT_NAME,
        "transit_speed_kmh": settings.TRANSIT_SPEED_KMH,
        "default_radius_km": 10.0,
        "platform_fee_percent": 10.0,
        "seeded_at": now_iso,
        "version": "1.1.0"
    }
    db.set_document("system_config", "main", sys_config)

    # 5. Delegate to core seed routine for business entities
    from seed import seed_database as run_business_seed
    print("[*] Seeding default users, workers, jobs, and offers...")
    run_business_seed()

    # 6. Verification
    if verify:
        print("\n[*] Verifying collection counts...")
        for col in collections:
            docs = db.list_collection(col)
            print(f"    - {col:15}: {len(docs)} documents")

    print("\n[SUCCESS] Database initialization and migration completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="RepairBuddy Database Migration & Seeding Tool")
    parser.add_argument("--clean", action="store_true", help="Clear collections prior to seeding")
    parser.add_argument("--remote", action="store_true", help="Require a live remote Firestore instance")
    parser.add_argument("--verify", action="store_true", default=True, help="Verify collection document counts")

    args = parser.parse_args()
    try:
        seed_database(clean=args.clean, require_remote=args.remote, verify=args.verify)
    except Exception as exc:
        print(f"\n[ERROR] Seeding failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

