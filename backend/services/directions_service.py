"""Directions Service — ORS Directions API -> polyline encoded, fallback garis lurus."""
import logging

import httpx

from core.config import settings
from services.distance_service import haversine_m

logger = logging.getLogger(__name__)

ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/json"


def encode_polyline(coords: list[tuple[float, float]]) -> str:
    """Encode polyline5 (format Google/ORS) dari list (lat, lng)."""
    precision = 5
    factor = 10**precision
    out = []
    prev_lat = prev_lng = 0
    for lat, lng in coords:
        lat5 = round(lat * factor)
        lng5 = round(lng * factor)

        def _enc(delta):
            delta <<= 1
            if delta < 0:
                delta = ~delta
            chunk = []
            while delta >= 0x20:
                chunk.append(chr((0x20 | (delta & 0x1F)) + 63))
                delta >>= 5
            chunk.append(chr(delta + 63))
            return "".join(chunk)

        out.append(_enc(lat5 - prev_lat))
        out.append(_enc(lng5 - prev_lng))
        prev_lat, prev_lng = lat5, lng5
    return "".join(out)


def _fallback_polyline(coords: list[tuple[float, float]]) -> str:
    """Garis lurus antar titik (visualisasi saja)."""
    return encode_polyline(coords)


def get_polyline(coords: list[tuple[float, float]]) -> str:
    """coords: list (lat, lng) urut rute -> encoded polyline."""
    if not coords:
        return ""
    if settings.USE_MOCK_MODE or not settings.ORS_API_KEY:
        return _fallback_polyline(coords)

    locations = [[lng, lat] for lat, lng in coords]
    try:
        resp = httpx.post(
            ORS_DIRECTIONS_URL,
            headers={"Authorization": settings.ORS_API_KEY},
            json={"coordinates": locations, "instructions": False},
            timeout=max(settings.REQUEST_TIMEOUT * 4, 20),
        )
        resp.raise_for_status()
        data = resp.json()
        geometry = data["routes"][0]["geometry"]
        if geometry:
            return geometry
    except Exception as exc:
        logger.warning("ORS Directions API gagal (%s), fallback polyline lurus.", exc)

    if settings.ENABLE_FALLBACK:
        return _fallback_polyline(coords)
    raise RuntimeError("Directions gagal dibuat.")
