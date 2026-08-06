import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/json"


def encode_polyline(coords: list[tuple[float, float]]) -> str:
    factor = 100000
    output = []
    previous_lat = previous_lng = 0
    for lat, lng in coords:
        lat_value = round(lat * factor)
        lng_value = round(lng * factor)
        for delta in (lat_value - previous_lat, lng_value - previous_lng):
            value = ~(delta << 1) if delta < 0 else delta << 1
            while value >= 0x20:
                output.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            output.append(chr(value + 63))
        previous_lat, previous_lng = lat_value, lng_value
    return "".join(output)


def get_polyline(coords: list[tuple[float, float]]) -> str:
    if not coords:
        return ""
    if settings.USE_MOCK_MODE or not settings.ORS_API_KEY:
        return encode_polyline(coords)
    try:
        response = httpx.post(
            ORS_DIRECTIONS_URL,
            headers={"Authorization": settings.ORS_API_KEY},
            json={
                "coordinates": [[lng, lat] for lat, lng in coords],
                "instructions": False,
            },
            timeout=max(settings.REQUEST_TIMEOUT * 4, 20),
        )
        response.raise_for_status()
        geometry = response.json()["routes"][0]["geometry"]
        if geometry:
            return geometry
    except Exception as exc:
        logger.warning("ORS Directions gagal: %s", exc)
    if settings.ENABLE_FALLBACK:
        return encode_polyline(coords)
    raise RuntimeError("Directions gagal dibuat.")
