import copy
import re
from typing import Any, Dict, Optional


def obfuscate_address(address_str: Optional[str]) -> str:
    """
    Masks granular street/building details from an address string.
    Transforms e.g.:
      "123 Main Street, Apt 4B, Sector 5" -> "Sector 5"
      "Flat 402, Building 7, Shanti Nagar, Mira Road East, Mumbai" -> "Mira Road East, Mumbai"
      "Mira Road, Mumbai" -> "Mira Road, Mumbai"
    """
    if not address_str or not isinstance(address_str, str):
        return "Approximate Area"

    stripped = address_str.strip()
    if not stripped:
        return "Approximate Area"

    parts = [p.strip() for p in stripped.split(",") if p.strip()]
    if not parts:
        return "Approximate Area"

    if len(parts) == 1:
        cleaned = re.sub(
            r'^(?:(?:apt|flat|room|unit|suite|no|bldg|building|door)\.?\s*[\w\d\-]+[\s,]*)+',
            '',
            parts[0],
            flags=re.IGNORECASE
        ).strip()
        cleaned = re.sub(
            r'^\d+\s+[\w\s]+(?:street|st|road|rd|avenue|ave|lane|ln|drive|dr)[\s,]*',
            '',
            cleaned,
            flags=re.IGNORECASE
        ).strip()
        return cleaned or parts[0]

    # Sensitive/granular building markers to exclude
    sensitive_markers = (
        "apt", "flat", "floor", "building", "bldg", "room", "house",
        "door", "street", "road no", "lane", "plot", "gala", "shop no", "chawl"
    )

    cleaned_parts = [
        p for p in parts
        if not any(marker in p.lower() for marker in sensitive_markers)
        and not (len(p) <= 5 and any(ch.isdigit() for ch in p))
    ]

    if cleaned_parts:
        if len(cleaned_parts) >= 2:
            return f"{cleaned_parts[-2]}, {cleaned_parts[-1]}"
        return cleaned_parts[-1]

    return parts[-1]


def serialize_worker(
    worker_data: Dict[str, Any],
    requester: Optional[Dict[str, Any]] = None,
    mask_for_public: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Serializes a worker profile, applying strict privacy controls:
    - Owner view (requester == worker.uid or requester role == 'admin'):
      Returns complete schema including phone and exact address.
    - Public view (requester != worker.uid and non-admin):
      Strips phone/phone_number, national_id, documentNumber, bank_details,
      obfuscates street address, and truncates exact coordinates.
    """
    if not worker_data:
        return {}

    res = copy.deepcopy(worker_data)
    worker_owner = res.get("owner_uid") or res.get("uid")

    is_owner = False
    is_admin = False

    if requester:
        req_uid = requester.get("uid")
        req_role = requester.get("role")
        is_owner = bool(req_uid and worker_owner and req_uid == worker_owner)
        is_admin = bool(req_role == "admin")

    should_mask = mask_for_public if mask_for_public is not None else not (is_owner or is_admin)

    if should_mask:
        # 1. Strip sensitive direct identifiers
        sensitive_keys = [
            "phone", "phone_number", "phoneNumber",
            "national_id", "nationalId",
            "documentNumber", "document_number", "documentNumberMasked",
            "bank_details", "bankDetails",
            "aadhaar", "pan", "voter_id", "passport"
        ]
        for key in sensitive_keys:
            res.pop(key, None)

        # 2. Obfuscate address and truncate precise coordinates
        if "location" in res and isinstance(res["location"], dict):
            loc = dict(res["location"])
            raw_addr = loc.get("address")
            if raw_addr:
                loc["address"] = obfuscate_address(raw_addr)
            if "lat" in loc and isinstance(loc["lat"], (int, float)):
                loc["lat"] = round(float(loc["lat"]), 2)
            if "lng" in loc and isinstance(loc["lng"], (int, float)):
                loc["lng"] = round(float(loc["lng"]), 2)
            res["location"] = loc

    return res
