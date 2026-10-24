import math
from core.config import settings


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle distance between two points on the Earth surface
    in kilometers using the Haversine formula.
    """
    R = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c
    return distance


def calculate_eta(distance_km: float, speed_kmh: float = None) -> float:
    """
    Calculates ETA in minutes based on distance and transit speed (default 25 km/h per PRD).
    """
    if speed_kmh is None:
        speed_kmh = settings.TRANSIT_SPEED_KMH

    if speed_kmh <= 0:
        return 0.0

    hours = distance_km / speed_kmh
    return hours * 60.0


def is_within_30_minutes(eta_minutes: float) -> bool:
    """
    Returns True if estimated arrival time is within 30 minutes.
    """
    return eta_minutes <= 30.0
