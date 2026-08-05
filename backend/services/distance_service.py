"""Distance Service — OpenRouteService Matrix API dengan fallback Haversine."""
import logging
from math import asin, cos, radians, sin, sqrt

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/driving-car/json"
DEFAULT_SPEED_KMH = 30.0  # kota; 50 jika dianggap tol


def haversine_m(lat1, lng1, lat2, lng2) -> float:
    """Jarak geodesik dalam meter."""
    r = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lng2 - lng1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _fallback_matrix(points: list[dict]) -> tuple[list[list[float]], list[list[float]]]:
    """Hitung jarak (meter) & durasi (detik) dengan Haversine."""
    n = len(points)
    distances = [[0.0] * n for _ in range(n)]
    durations = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = haversine_m(
                points[i]["lat"], points[i]["lng"], points[j]["lat"], points[j]["lng"]
            )
            distances[i][j] = d
            durations[i][j] = d / (DEFAULT_SPEED_KMH / 3.6)
    return distances, durations


def get_distance_matrix(points: list[dict]) -> tuple[list[list[float]], list[list[float]]]:
    """points: [{lat, lng}, ...]. Return (distance_m, duration_s) matrix n×n."""
    if settings.USE_MOCK_MODE or not settings.ORS_API_KEY:
        return _fallback_matrix(points)

    locations = [[p["lng"], p["lat"]] for p in points]
    try:
        resp = httpx.post(
            ORS_MATRIX_URL,
            headers={"Authorization": settings.ORS_API_KEY},
            json={
                "locations": locations,
                "metrics": ["distance", "duration"],
                "resolve_locations": False,
            },
            timeout=max(settings.REQUEST_TIMEOUT * 4, 20),
        )
        resp.raise_for_status()
        data = resp.json()
        distances = data["distances"]
        durations = data["durations"]
        # Normalisasi None (OR sinkronisasi) -> 0
        n = len(points)
        distances = [
            [distances[i][j] if distances[i][j] is not None else 0.0 for j in range(n)]
            for i in range(n)
        ]
        durations = [
            [durations[i][j] if durations[i][j] is not None else 0.0 for j in range(n)]
            for i in range(n)
        ]
        return distances, durations
    except Exception as exc:
        logger.warning("ORS Matrix API gagal (%s), fallback Haversine.", exc)

    if settings.ENABLE_FALLBACK:
        return _fallback_matrix(points)
    raise RuntimeError("Distance matrix gagal dihitung.")
