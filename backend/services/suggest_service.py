"""Suggest Service — autocomplete alamat ala Google Maps.

Primary: Photon (komoot) — gratis, search-as-you-type, tanpa API key,
akurat untuk alamat Indonesia (OSM). Bias ke lokasi gudang (Jakarta).
Fallback: OpenCage geocoding limit=5 bila Photon gagal.
"""
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

PHOTON_URL = "https://photon.komoot.io/api/"
OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"

# Photon memblokir User-Agent non-browser (403) — pakai UA browser.
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# Jakarta (lokasi gudang) sebagai bias geocoding
FOCUS_LAT = settings.ORIGIN_LAT
FOCUS_LNG = settings.ORIGIN_LNG

# Bounding box Jabodetabek (minLon,minLat,maxLon,maxLat) — filter keras
# agar jalan ambigu (Jl. Sudirman dll) tidak jatuh ke kota lain.
JABODETABEK_BBOX = "106.6,-6.5,107.1,-5.9"


def _to_suggestion(feature: dict) -> dict:
    """Normalisasi satu fitur Photon -> dict suggestion."""
    props = feature.get("properties", {})
    coords = feature.get("geometry", {}).get("coordinates", [])
    name = props.get("name", "")
    street = props.get("street", "")
    house = props.get("housenumber", "")
    district = props.get("district") or props.get("suburb") or props.get("locality") or ""
    city = props.get("city") or props.get("state") or ""
    # Label: jalan + no, [distrik], kota
    road = f"{street} {house}".strip() or name
    label_parts = [road, district, city, props.get("country", "")]
    label = ", ".join(p for p in label_parts if p)
    return {
        "label": label,
        "address": road or label,
        "lat": coords[1] if len(coords) >= 2 else None,
        "lng": coords[0] if len(coords) >= 2 else None,
    }


def _dedupe(suggestions: list[dict]) -> list[dict]:
    """Buang hasil duplikat (label sama persis atau koordinat hampir sama)."""
    seen_labels = set()
    seen_coords = set()
    out = []
    for s in suggestions:
        label_key = s["label"].lower().strip()
        coord_key = (round(s["lat"], 4), round(s["lng"], 4)) if s["lat"] is not None else None
        if label_key and label_key in seen_labels:
            continue
        if coord_key and coord_key in seen_coords:
            continue
        seen_labels.add(label_key)
        if coord_key:
            seen_coords.add(coord_key)
        out.append(s)
    return out


def suggest_photon(query: str, limit: int = 6) -> list[dict]:
    """Autocomplete via Photon, bias ke Jakarta + bbox Jabodetabek."""
    resp = httpx.get(
        PHOTON_URL,
        params={
            "q": query,
            "lat": FOCUS_LAT,
            "lon": FOCUS_LNG,
            "limit": limit,
            "countrycode": "id",
            "bbox": JABODETABEK_BBOX,
        },
        headers={"User-Agent": BROWSER_UA},
        timeout=settings.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    return _dedupe([_to_suggestion(f) for f in features if f.get("geometry")])


def suggest_opencage(query: str, limit: int = 6) -> list[dict]:
    """Fallback autocomplete via OpenCage geocoding (limit>1)."""
    resp = httpx.get(
        OPENCAGE_URL,
        params={
            "q": query,
            "key": settings.OPENCAGE_API_KEY,
            "limit": limit,
            "countrycode": "id",
            "proximity": f"{FOCUS_LAT},{FOCUS_LNG}",
            "language": "id",
            "no_annotations": 1,
        },
        timeout=settings.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    out = []
    for r in resp.json().get("results", []):
        geom = r.get("geometry", {})
        if not geom:
            continue
        out.append(
            {
                "label": r.get("formatted", ""),
                "address": r.get("formatted", ""),
                "lat": geom.get("lat"),
                "lng": geom.get("lng"),
            }
        )
    return out


def suggest(query: str, limit: int = 6) -> list[dict]:
    """Autocomplete alamat. Photon primary, OpenCage fallback."""
    query = query.strip()
    if len(query) < 3:
        return []
    try:
        return suggest_photon(query, limit)
    except Exception as exc:
        logger.warning("Photon gagal (%s), fallback OpenCage.", exc)

    if settings.ENABLE_FALLBACK and settings.OPENCAGE_API_KEY:
        try:
            return suggest_opencage(query, limit)
        except Exception as exc:
            logger.warning("OpenCage suggest gagal (%s).", exc)
    return []
