"""Geocoding Service — Photon (komoot) primary, OpenCage fallback.

Photon (OSM, gratis, search-as-you-type) jauh lebih akurat untuk alamat
Indonesia yang ambigu (Jl. Sudirman, dll) karena bisa dibias ke Jakarta.
Fallback terakhir: koordinat deterministik Jakarta Pusat (bukan random),
agar simulasi tetap stabil.
"""
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

PHOTON_URL = "https://photon.komoot.io/api/"
OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"

# Photon memblokir User-Agent non-browser (403) — pakai UA browser.
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# Jakarta (lokasi gudang) — bias geocoding & fallback deterministik
JAKARTA_CENTER = {"lat": settings.ORIGIN_LAT, "lng": settings.ORIGIN_LNG}

# Bounding box Jabodetabek (minLon,minLat,maxLon,maxLat) — filter keras
JABODETABEK_BBOX = "106.6,-6.5,107.1,-5.9"


def _fallback_coordinates(address: str) -> dict:
    """Koordinat deterministik (Jakarta Pusat). Bukan random."""
    return dict(JAKARTA_CENTER)


def _geocode_photon(address: str) -> dict:
    """Geocode via Photon; bias ke Jakarta, hanya ambil hasil terbaik."""
    resp = httpx.get(
        PHOTON_URL,
        params={
            "q": address,
            "lat": JAKARTA_CENTER["lat"],
            "lon": JAKARTA_CENTER["lng"],
            "limit": 1,
            "countrycode": "id",
            "bbox": JABODETABEK_BBOX,
        },
        headers={"User-Agent": BROWSER_UA},
        timeout=settings.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    if not features:
        return None
    coords = features[0].get("geometry", {}).get("coordinates", [])
    if len(coords) < 2:
        return None
    return {"lat": coords[1], "lng": coords[0]}


def _geocode_opencage(address: str) -> dict:
    """Fallback geocode via OpenCage dengan proximity Jakarta."""
    resp = httpx.get(
        OPENCAGE_URL,
        params={
            "q": address,
            "key": settings.OPENCAGE_API_KEY,
            "limit": 1,
            "language": "id",
            "countrycode": "id",
            "proximity": f"{JAKARTA_CENTER['lat']},{JAKARTA_CENTER['lng']}",
            "bounds": JABODETABEK_BBOX,
        },
        timeout=settings.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("results"):
        geom = data["results"][0]["geometry"]
        return {"lat": geom["lat"], "lng": geom["lng"]}
    return None


def geocode(address: str) -> dict:
    """Alamat -> {lat, lng}. Photon -> OpenCage -> Jakarta Pusat."""
    if settings.USE_MOCK_MODE:
        return _fallback_coordinates(address)

    # 1. Photon
    try:
        result = _geocode_photon(address)
        if result:
            return result
        logger.warning("Photon: tidak ada hasil untuk '%s'", address)
    except Exception as exc:
        logger.warning("Photon API gagal (%s), coba OpenCage.", exc)

    # 2. OpenCage
    if settings.OPENCAGE_API_KEY:
        try:
            result = _geocode_opencage(address)
            if result:
                return result
            logger.warning("OpenCage: tidak ada hasil untuk '%s'", address)
        except Exception as exc:
            logger.warning("OpenCage API gagal (%s).", exc)

    # 3. Fallback deterministik
    if settings.ENABLE_FALLBACK:
        logger.warning("Geocoding gagal untuk '%s', pakai Jakarta Pusat.", address)
        return _fallback_coordinates(address)
    raise RuntimeError(f"Geocoding gagal untuk: {address}")
