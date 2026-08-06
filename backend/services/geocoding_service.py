import hashlib
import logging
import re

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

PHOTON_URL = "https://photon.komoot.io/api/"
OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"
BROWSER_UA = "Mozilla/5.0 (compatible; Compfest18/1.0)"
JABODETABEK_BBOX = "106.6,-6.5,107.1,-5.9"


def _validated_coordinates(lat, lng):
    lat = float(lat)
    lng = float(lng)
    if not -90 <= lat <= 90 or not -180 <= lng <= 180:
        raise ValueError("Koordinat geocoding berada di luar range valid.")
    return lat, lng


def _metadata(properties: dict, source: str, confidence: float) -> dict:
    return {
        "source": source,
        "confidence": confidence,
        "city": properties.get("city") or properties.get("town") or properties.get("state"),
        "county": properties.get("county"),
        "state": properties.get("state"),
        "district": properties.get("district") or properties.get("suburb"),
        "locality": properties.get("locality"),
        "postcode": properties.get("postcode"),
    }


def _fallback_coordinates(address: str) -> dict:
    digest = hashlib.sha256(re.sub(r"\s+", " ", address.strip().lower()).encode()).digest()
    lat = -6.245 + (digest[0] / 255) * 0.09
    lng = 106.74 + (digest[1] / 255) * 0.14
    if abs(lat - settings.ORIGIN_LAT) < 0.001 and abs(lng - settings.ORIGIN_LNG) < 0.001:
        lng += 0.01
    return {
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "source": "mock",
        "confidence": 0.0,
        "is_fallback": True,
    }


def _geocode_photon(address: str) -> dict | None:
    response = httpx.get(
        PHOTON_URL,
        params={
            "q": address,
            "lat": settings.ORIGIN_LAT,
            "lon": settings.ORIGIN_LNG,
            "limit": 1,
            "countrycode": "id",
            "bbox": JABODETABEK_BBOX,
        },
        headers={"User-Agent": BROWSER_UA},
        timeout=settings.REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    features = response.json().get("features", [])
    if not features:
        return None
    feature = features[0]
    coordinates = feature.get("geometry", {}).get("coordinates", [])
    if len(coordinates) < 2:
        return None
    lat, lng = _validated_coordinates(coordinates[1], coordinates[0])
    result = {"lat": lat, "lng": lng}
    result.update(_metadata(feature.get("properties", {}), "photon", 0.8))
    return result


def _geocode_opencage(address: str) -> dict | None:
    response = httpx.get(
        OPENCAGE_URL,
        params={
            "q": address,
            "key": settings.OPENCAGE_API_KEY,
            "limit": 1,
            "language": "id",
            "countrycode": "id",
            "proximity": f"{settings.ORIGIN_LAT},{settings.ORIGIN_LNG}",
            "bounds": JABODETABEK_BBOX,
        },
        timeout=settings.REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return None
    result = results[0]
    geometry = result.get("geometry", {})
    lat, lng = _validated_coordinates(geometry["lat"], geometry["lng"])
    output = {"lat": lat, "lng": lng}
    output.update(_metadata(result.get("components", {}), "opencage", 0.85))
    return output


def geocode(address: str, allow_mock: bool = False) -> dict:
    if settings.USE_MOCK_MODE:
        return _fallback_coordinates(address)

    try:
        result = _geocode_photon(address)
        if result:
            return result
    except Exception as exc:
        logger.warning("Photon geocoding gagal: %s", exc)

    if settings.OPENCAGE_API_KEY:
        try:
            result = _geocode_opencage(address)
            if result:
                return result
        except Exception as exc:
            logger.warning("OpenCage geocoding gagal: %s", exc)

    if allow_mock:
        logger.warning("Geocoding gagal untuk '%s', menggunakan koordinat mock.", address)
        return _fallback_coordinates(address)
    raise RuntimeError(f"Alamat tidak dapat diverifikasi: {address}")
