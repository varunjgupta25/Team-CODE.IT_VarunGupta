import os
import sys
from datetime import datetime, timezone

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import db
from services.trust import get_worker_trust_info


def seed_database():
    print("[INFO] Starting RepairBuddy Database Seeding...")

    # Clear existing data for a clean slate
    for collection in ["users", "workers", "jobs", "offers", "reviews", "sos_alerts", "reports"]:
        db.clear_collection(collection)

    # 1. Seed 5 Customers + 1 Admin
    customers = [
        {
            "uid": "cust_priya",
            "role": "customer",
            "name": "Priya Sharma",
            "phone": "+91 98201 11222",
            "language": "en",
            "location": {"lat": 19.2825, "lng": 72.8570, "address": "Flat 402, Beverly Park, Mira Road East, Mumbai"}
        },
        {
            "uid": "cust_amit",
            "role": "customer",
            "name": "Amit Verma",
            "phone": "+91 98202 22333",
            "language": "hi",
            "location": {"lat": 19.2860, "lng": 72.8620, "address": "B-12, Poonam Sagar Complex, Mira Road East, Mumbai"}
        },
        {
            "uid": "cust_sneha",
            "role": "customer",
            "name": "Sneha Kulkarni",
            "phone": "+91 98203 33444",
            "language": "mr",
            "location": {"lat": 19.2790, "lng": 72.8540, "address": "Building 5, Shanti Nagar Sector 3, Mira Road East, Mumbai"}
        },
        {
            "uid": "cust_rahul",
            "role": "customer",
            "name": "Rahul Mehta",
            "phone": "+91 98204 44555",
            "language": "en",
            "location": {"lat": 19.2900, "lng": 72.8590, "address": "Wing A, Jangid Enclave, Kanakia Road, Mira Road, Mumbai"}
        },
        {
            "uid": "cust_ananya",
            "role": "customer",
            "name": "Ananya Deshmukh",
            "phone": "+91 98205 55666",
            "language": "mr",
            "location": {"lat": 19.2750, "lng": 72.8510, "address": "Sheetal Nagar Road, Near Station, Mira Road East, Mumbai"}
        },
        {
            "uid": "admin_user",
            "role": "admin",
            "name": "Super Admin",
            "phone": "+91 99999 00000",
            "language": "en",
            "location": {"lat": 19.2825, "lng": 72.8570, "address": "RepairBuddy Admin HQ, Mumbai"}
        }
    ]

    for c in customers:
        db.set_document("users", c["uid"], c)
    print(f"[OK] Seeded {len(customers)} users (5 customers, 1 admin).")

    # 2. Seed 25 Workers across 6 categories around Mira Road, Mumbai
    # Categories: plumber, electrician, painter, cleaner, maid, cook
    # Coordinates centered around Lat: 19.2812, Lng: 72.8561
    raw_workers = [
        # --- Plumbers (5 workers: 4 verified, 1 unverified) ---
        {
            "uid": "worker_plumber_1",
            "name": "Ramesh Kumar",
            "phone": "+91 91101 00001",
            "skills": ["plumber"],
            "rates": {"plumber": 350.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 42,
            "location": {"lat": 19.2830, "lng": 72.8580},
            "serviceRadiusKm": 6.0,
            "avatarUrl": "https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80",
            "about": "10+ years expert in pipe fitting, leak repair & bathroom sanitary fixtures."
        },
        {
            "uid": "worker_plumber_2",
            "name": "Suresh Sharma",
            "phone": "+91 91101 00002",
            "skills": ["plumber", "cleaner"],
            "rates": {"plumber": 400.0, "cleaner": 300.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.7,
            "jobsDone": 28,
            "location": {"lat": 19.2805, "lng": 72.8550},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
            "about": "Water motor installation, overhead tank cleanup & drainage repair specialist."
        },
        {
            "uid": "worker_plumber_3",
            "name": "Santosh Gupta",
            "phone": "+91 91101 00003",
            "skills": ["plumber"],
            "rates": {"plumber": 300.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.5,
            "jobsDone": 19,
            "location": {"lat": 19.2880, "lng": 72.8600},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
            "about": "Affordable home plumbing, geyser fittings, and quick tap replacements."
        },
        {
            "uid": "worker_plumber_4",
            "name": "Vijay Gaikwad",
            "phone": "+91 91101 00004",
            "skills": ["plumber"],
            "rates": {"plumber": 450.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.8,
            "jobsDone": 35,
            "location": {"lat": 19.2770, "lng": 72.8520},
            "serviceRadiusKm": 7.0,
            "avatarUrl": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150&auto=format&fit=crop&q=80",
            "about": "Master plumber for commercial and residential deep piping & emergency unclogging."
        },
        {
            # UNVERIFIED PLUMBER (Used to prove unverified filtering in live pitch)
            "uid": "worker_plumber_unverified",
            "name": "Kamlesh Verma",
            "phone": "+91 91101 00005",
            "skills": ["plumber"],
            "rates": {"plumber": 250.0},
            "isAvailableNow": True,
            "verified": False,
            "verificationStatus": "unverified",
            "rating": 3.8,
            "jobsDone": 2,
            "location": {"lat": 19.2820, "lng": 72.8575},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80",
            "about": "Unverified trainee plumber awaiting document verification."
        },

        # --- Electricians (5 workers: 4 verified, 1 unverified) ---
        {
            "uid": "worker_elec_1",
            "name": "Rajesh Patel",
            "phone": "+91 91102 00001",
            "skills": ["electrician"],
            "rates": {"electrician": 450.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 51,
            "location": {"lat": 19.2840, "lng": 72.8590},
            "serviceRadiusKm": 6.0,
            "avatarUrl": "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=150&auto=format&fit=crop&q=80",
            "about": "Certified wireman with 8+ years experience in MCB, short-circuit & wiring."
        },
        {
            "uid": "worker_elec_2",
            "name": "Manoj Yadav",
            "phone": "+91 91102 00002",
            "skills": ["electrician"],
            "rates": {"electrician": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.6,
            "jobsDone": 23,
            "location": {"lat": 19.2810, "lng": 72.8540},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=150&auto=format&fit=crop&q=80",
            "about": "Fan installation, switchboard repair & inverter connection specialist."
        },
        {
            "uid": "worker_elec_3",
            "name": "Sunil Verma",
            "phone": "+91 91102 00003",
            "skills": ["electrician", "plumber"],
            "rates": {"electrician": 500.0, "plumber": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.8,
            "jobsDone": 38,
            "location": {"lat": 19.2785, "lng": 72.8530},
            "serviceRadiusKm": 6.5,
            "avatarUrl": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80",
            "about": "Dual-trade electrician and motor mechanic for residential apartments."
        },
        {
            "uid": "worker_elec_4",
            "name": "Dinesh Mourya",
            "phone": "+91 91102 00004",
            "skills": ["electrician"],
            "rates": {"electrician": 350.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.4,
            "jobsDone": 14,
            "location": {"lat": 19.2870, "lng": 72.8615},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=150&auto=format&fit=crop&q=80",
            "about": "Rapid appliance setup, LED fixtures, chandelier assembly and wiring."
        },
        {
            # UNVERIFIED ELECTRICIAN
            "uid": "worker_elec_unverified",
            "name": "Ajay Rawat",
            "phone": "+91 91102 00005",
            "skills": ["electrician"],
            "rates": {"electrician": 300.0},
            "isAvailableNow": True,
            "verified": False,
            "verificationStatus": "pending",
            "rating": 4.0,
            "jobsDone": 1,
            "location": {"lat": 19.2835, "lng": 72.8570},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
            "about": "Unverified electrician apprentice."
        },

        # --- Cleaners (4 workers: 3 verified, 1 unverified) ---
        {
            "uid": "worker_cleaner_1",
            "name": "Anita Kamble",
            "phone": "+91 91103 00001",
            "skills": ["cleaner", "maid"],
            "rates": {"cleaner": 350.0, "maid": 300.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 64,
            "location": {"lat": 19.2815, "lng": 72.8565},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80",
            "about": "Deep home cleaning, bathroom sanitization, tile scrubbing & kitchen degreasing."
        },
        {
            "uid": "worker_cleaner_2",
            "name": "Deepak Chauhan",
            "phone": "+91 91103 00002",
            "skills": ["cleaner"],
            "rates": {"cleaner": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.7,
            "jobsDone": 29,
            "location": {"lat": 19.2855, "lng": 72.8610},
            "serviceRadiusKm": 6.0,
            "avatarUrl": "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?w=150&auto=format&fit=crop&q=80",
            "about": "Sofa shampooing, carpet deep dry cleaning, balcony and window glass wash."
        },
        {
            "uid": "worker_cleaner_3",
            "name": "Sunita Pawar",
            "phone": "+91 91103 00003",
            "skills": ["cleaner", "maid"],
            "rates": {"cleaner": 300.0, "maid": 250.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.6,
            "jobsDone": 22,
            "location": {"lat": 19.2795, "lng": 72.8535},
            "serviceRadiusKm": 4.5,
            "avatarUrl": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80",
            "about": "Domestic floor scrubbing, balcony wash, kitchen chimney cleanup."
        },
        {
            # UNVERIFIED CLEANER
            "uid": "worker_cleaner_unverified",
            "name": "Pooja Jadhav",
            "phone": "+91 91103 00004",
            "skills": ["cleaner"],
            "rates": {"cleaner": 250.0},
            "isAvailableNow": True,
            "verified": False,
            "verificationStatus": "pending",
            "rating": 4.1,
            "jobsDone": 3,
            "location": {"lat": 19.2828, "lng": 72.8582},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80",
            "about": "New cleaner registration pending verification."
        },

        # --- Painters (4 workers: 3 verified, 1 unverified) ---
        {
            "uid": "worker_painter_1",
            "name": "Ganesh Shinde",
            "phone": "+91 91104 00001",
            "skills": ["painter"],
            "rates": {"painter": 600.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.8,
            "jobsDone": 33,
            "location": {"lat": 19.2838, "lng": 72.8578},
            "serviceRadiusKm": 7.0,
            "avatarUrl": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=150&auto=format&fit=crop&q=80",
            "about": "Interior emulsion, texture wall painting & waterproof primer specialist."
        },
        {
            "uid": "worker_painter_2",
            "name": "Arjun Prajapati",
            "phone": "+91 91104 00002",
            "skills": ["painter"],
            "rates": {"painter": 550.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.6,
            "jobsDone": 20,
            "location": {"lat": 19.2875, "lng": 72.8625},
            "serviceRadiusKm": 6.0,
            "avatarUrl": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80",
            "about": "Repainting, dampness treatment, wall putty finish & door polish."
        },
        {
            "uid": "worker_painter_3",
            "name": "Vinod Vishwakarma",
            "phone": "+91 91104 00003",
            "skills": ["painter"],
            "rates": {"painter": 700.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 45,
            "location": {"lat": 19.2765, "lng": 72.8505},
            "serviceRadiusKm": 8.0,
            "avatarUrl": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
            "about": "Master painter with Asian Paints certification for luxury residential decor."
        },
        {
            # UNVERIFIED PAINTER
            "uid": "worker_painter_unverified",
            "name": "Raju Kanojia",
            "phone": "+91 91104 00004",
            "skills": ["painter"],
            "rates": {"painter": 450.0},
            "isAvailableNow": True,
            "verified": False,
            "verificationStatus": "pending",
            "rating": 3.9,
            "jobsDone": 0,
            "location": {"lat": 19.2818, "lng": 72.8568},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=150&auto=format&fit=crop&q=80",
            "about": "Unverified local painter."
        },

        # --- Maids (4 workers: 4 verified) ---
        {
            "uid": "worker_maid_1",
            "name": "Lakshmi Bai",
            "phone": "+91 91105 00001",
            "skills": ["maid", "cleaner"],
            "rates": {"maid": 300.0, "cleaner": 350.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 58,
            "location": {"lat": 19.2822, "lng": 72.8560},
            "serviceRadiusKm": 4.0,
            "avatarUrl": "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?w=150&auto=format&fit=crop&q=80",
            "about": "Reliable daily housekeeping, utensils wash, dusting and clothes ironing."
        },
        {
            "uid": "worker_maid_2",
            "name": "Rekha Solanki",
            "phone": "+91 91105 00002",
            "skills": ["maid", "cook"],
            "rates": {"maid": 350.0, "cook": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.7,
            "jobsDone": 27,
            "location": {"lat": 19.2865, "lng": 72.8630},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80",
            "about": "Full home sweeping, mopping, bathroom cleaning & vegetable chopping."
        },
        {
            "uid": "worker_maid_3",
            "name": "Geeta Devi",
            "phone": "+91 91105 00003",
            "skills": ["maid"],
            "rates": {"maid": 250.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.5,
            "jobsDone": 18,
            "location": {"lat": 19.2780, "lng": 72.8530},
            "serviceRadiusKm": 4.5,
            "avatarUrl": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80",
            "about": "Morning & evening house cleaning, dishwashing & laundry support."
        },
        {
            "uid": "worker_maid_4",
            "name": "Kavita Salvi",
            "phone": "+91 91105 00004",
            "skills": ["maid"],
            "rates": {"maid": 280.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.8,
            "jobsDone": 31,
            "location": {"lat": 19.2890, "lng": 72.8595},
            "serviceRadiusKm": 5.5,
            "avatarUrl": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80",
            "about": "Quick on-demand flat cleaning and pre-guest house organization."
        },

        # --- Cooks (3 workers: 3 verified) ---
        {
            "uid": "worker_cook_1",
            "name": "Bablu Maharaj",
            "phone": "+91 91106 00001",
            "skills": ["cook"],
            "rates": {"cook": 500.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.9,
            "jobsDone": 47,
            "location": {"lat": 19.2832, "lng": 72.8572},
            "serviceRadiusKm": 6.0,
            "avatarUrl": "https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80",
            "about": "Expert in North Indian, Gujarati, Marwari & homestyle thali meals."
        },
        {
            "uid": "worker_cook_2",
            "name": "Radha Devi",
            "phone": "+91 91106 00002",
            "skills": ["cook", "maid"],
            "rates": {"cook": 450.0, "maid": 300.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.8,
            "jobsDone": 39,
            "location": {"lat": 19.2800, "lng": 72.8545},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1544717305-2782549b5136?w=150&auto=format&fit=crop&q=80",
            "about": "Pure vegetarian Maharashtrian, Jain food, rotis & healthy sabzis."
        },
        {
            "uid": "worker_cook_3",
            "name": "Shyam Sundar",
            "phone": "+91 91106 00003",
            "skills": ["cook"],
            "rates": {"cook": 400.0},
            "isAvailableNow": True,
            "verified": True,
            "rating": 4.6,
            "jobsDone": 21,
            "location": {"lat": 19.2850, "lng": 72.8605},
            "serviceRadiusKm": 5.0,
            "avatarUrl": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
            "about": "Fast party snacks, dal tadka, biryanis & daily tiffin cooking."
        }
    ]

    for w in raw_workers:
        trust_score, trust_badge = get_worker_trust_info(w)
        w["trustScore"] = trust_score
        w["trustBadge"] = trust_badge

        # Save worker document
        db.set_document("workers", w["uid"], w)

        # Also create matching user record for auth resolution
        user_record = {
            "uid": w["uid"],
            "role": "worker",
            "name": w["name"],
            "phone": w["phone"],
            "language": "hi",
            "location": w["location"]
        }
        db.set_document("users", w["uid"], user_record)

    print(f"[OK] Seeded {len(raw_workers)} workers (21 verified, 4 unverified) across 6 categories.")

    # 3. Seed 5 Initial Jobs across different categories & states
    now_iso = datetime.now(timezone.utc).isoformat()
    jobs = [
        {
            "id": "job_seed_plumber_open",
            "customerId": "cust_priya",
            "category": "plumber",
            "description": "Kitchen sink pipe leakage, water dripping under counter",
            "location": {
                "lat": 19.2825,
                "lng": 72.8570,
                "address": "Flat 402, Beverly Park, Mira Road East, Mumbai"
            },
            "budget": 400.0,
            "mode": "on-demand",
            "status": "open",
            "acceptedWorkerId": None,
            "finalPrice": None,
            "createdAt": now_iso
        },
        {
            "id": "job_seed_elec_negotiating",
            "customerId": "cust_amit",
            "category": "electrician",
            "description": "Short circuit in bedroom MCB tripping repeatedly",
            "location": {
                "lat": 19.2860,
                "lng": 72.8620,
                "address": "B-12, Poonam Sagar Complex, Mira Road East, Mumbai"
            },
            "budget": 500.0,
            "mode": "on-demand",
            "status": "negotiating",
            "acceptedWorkerId": None,
            "finalPrice": None,
            "createdAt": now_iso
        },
        {
            "id": "job_seed_cleaner_accepted",
            "customerId": "cust_sneha",
            "category": "cleaner",
            "description": "Deep cleaning for 2BHK flat bathroom and kitchen",
            "location": {
                "lat": 19.2790,
                "lng": 72.8540,
                "address": "Building 5, Shanti Nagar Sector 3, Mira Road East, Mumbai"
            },
            "budget": 800.0,
            "mode": "on-demand",
            "status": "accepted",
            "acceptedWorkerId": "worker_cleaner_1",
            "finalPrice": 850.0,
            "createdAt": now_iso
        },
        {
            "id": "job_seed_painter_progress",
            "customerId": "cust_rahul",
            "category": "painter",
            "description": "Touchup painting for living room wall moisture patch",
            "location": {
                "lat": 19.2900,
                "lng": 72.8590,
                "address": "Wing A, Jangid Enclave, Kanakia Road, Mira Road, Mumbai"
            },
            "budget": 600.0,
            "mode": "on-demand",
            "status": "in_progress",
            "acceptedWorkerId": "worker_painter_1",
            "finalPrice": 600.0,
            "createdAt": now_iso
        },
        {
            "id": "job_seed_cook_completed",
            "customerId": "cust_ananya",
            "category": "cook",
            "description": "North Indian dinner preparation for 4 family members",
            "location": {
                "lat": 19.2750,
                "lng": 72.8510,
                "address": "Sheetal Nagar Road, Near Station, Mira Road East, Mumbai"
            },
            "budget": 450.0,
            "mode": "on-demand",
            "status": "completed",
            "acceptedWorkerId": "worker_cook_1",
            "finalPrice": 450.0,
            "createdAt": now_iso
        }
    ]

    for j in jobs:
        db.set_document("jobs", j["id"], j)
    print(f"[OK] Seeded {len(jobs)} jobs (open, negotiating, accepted, in_progress, completed).")

    # 4. Seed an initial pending offer for the negotiating job
    seed_offer = {
        "id": "offer_seed_demo_1",
        "jobId": "job_seed_elec_negotiating",
        "workerId": "worker_elec_1",
        "price": 550.0,
        "by": "worker",
        "status": "pending",
        "createdAt": now_iso
    }
    db.set_document("offers", seed_offer["id"], seed_offer)
    print("[OK] Seeded initial pending offer for negotiation demo.")

    print("\n[DONE] Seeding complete! Database is populated and ready for demo.")


if __name__ == "__main__":
    seed_database()
