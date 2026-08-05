"""Geocoding Service — OpenCage API dengan fallback mock + random sekitar Jakarta."""
import json
import logging
import random

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"
JAKARTA_CENTER = (-6.2, 106.816666)
JITTER = 0.05

# Koordinat landmark populer untuk demo (biar deterministik)
MOCK_COORDINATES = {
    "sudirman": {"lat": -6.2244, "lng": 106.8090},
    "gatot subroto": {"lat": -6.2222, "lng": 106.8292},
    "thamrin": {"lat": -6.1953, "lng": 106.8231},
    "bandung": {"lat": -6.9175, "lng": 107.6191},
    "surabaya": {"lat": -7.2575, "lng": 112.7521},
    "yogyakarta": {"lat": -7.7956, "lng": 110.3695},
    "semarang": {"lat": -6.9667, "lng": 110.4167},
    "medan": {"lat": 3.5952, "lng": 98.6722},
    "makassar": {"lat": -5.1477, "lng": 119.4327},
    "palembang": {"lat": -2.9761, "lng": 104.7754},
    "denpasar": {"lat": -8.6705, "lng": 115.2126},
    "malang": {"lat": -7.9666, "lng": 112.6326},
    "bogor": {"lat": -6.5971, "lng": 106.8060},
    "depok": {"lat": -6.4025, "lng": 106.7942},
    "bekasi": {"lat": -6.2383, "lng": 106.9756},
    "tangerang": {"lat": -6.1783, "lng": 106.6319},
}


def get_mock_coordinates(address: str) -> dict:
    addr_lower = address.lower()
    for key, coord in MOCK_COORDINATES.items():
        if key in addr_lower:
            return dict(coord)
    lat = JAKARTA_CENTER[0] + random.uniform(-JITTER, JITTER)
    lng = JAKARTA_CENTER[1] + random.uniform(-JITTER, JITTER)
    return {"lat": round(lat, 6), "lng": round(lng, 6)}


def geocode(address: str) -> dict:
    """Alamat -> {lat, lng}. Pakai OpenCage, fallback ke mock jika gagal."""
    if settings.USE_MOCK_MODE or not settings.OPENCAGE_API_KEY:
        return get_mock_coordinates(address)

    try:
        resp = httpx.get(
            OPENCAGE_URL,
            params={
                "q": address,
                "key": settings.OPENCAGE_API_KEY,
                "limit": 1,
                "language": "id",
                "countrycode": "id",
            },
            timeout=settings.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("results"):
            geom = data["results"][0]["geometry"]
            return {"lat": geom["lat"], "lng": geom["lng"]}
        logger.warning("OpenCage: tidak ada hasil untuk '%s'", address)
    except Exception as exc:
        logger.warning("OpenCage API gagal (%s), fallback ke mock.", exc)

    if settings.ENABLE_FALLBACK:
        return get_mock_coordinates(address)
    raise RuntimeError(f"Geocoding gagal untuk: {address}")
