import logging

import httpx

from core.config import settings
from core.database import find_adm2_from_address, find_adm4_from_address, find_adm4_from_location

logger = logging.getLogger(__name__)

BMKG_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
DEFAULT_WEATHER = "Cerah"
DEFAULT_TEMP = 30


def _fallback(source: str = "fallback") -> dict:
    return {
        "weather": DEFAULT_WEATHER,
        "temperature": DEFAULT_TEMP,
        "adm4_code": None,
        "source": source,
        "is_fallback": True,
    }


def _extract_weather(data: dict) -> tuple[str, float]:
    try:
        forecast = data["data"][0]["cuaca"]
        rows = forecast[0] if forecast and isinstance(forecast[0], list) else forecast
        for item in rows:
            if not isinstance(item, dict) or not item.get("weather_desc"):
                continue
            try:
                temperature = float(item.get("t", DEFAULT_TEMP))
            except (TypeError, ValueError):
                temperature = DEFAULT_TEMP
            return str(item["weather_desc"]), temperature
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        logger.warning("Parsing BMKG gagal: %s", exc)
    return DEFAULT_WEATHER, DEFAULT_TEMP


def get_weather_for_location(address: str, location: dict | None = None) -> dict:
    if settings.USE_MOCK_MODE:
        return _fallback("mock")

    location = location or {}
    adm4 = find_adm4_from_location(location, address)
    adm4 = adm4 or find_adm4_from_address(address)
    adm4 = adm4 or find_adm2_from_address(address)
    if not adm4:
        if settings.ENABLE_FALLBACK:
            return _fallback()
        raise RuntimeError(f"Kode wilayah BMKG tidak ditemukan untuk: {address}")

    try:
        response = httpx.get(
            BMKG_URL,
            params={"adm4": adm4},
            timeout=settings.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        weather, temperature = _extract_weather(response.json())
        return {
            "weather": weather,
            "temperature": temperature,
            "adm4_code": adm4,
            "source": "bmkg",
            "is_fallback": False,
        }
    except Exception as exc:
        logger.warning("BMKG gagal untuk %s: %s", adm4, exc)
        if settings.ENABLE_FALLBACK:
            result = _fallback()
            result["adm4_code"] = adm4
            return result
        raise RuntimeError(f"Cuaca BMKG gagal diperoleh untuk: {address}") from exc


def get_weather_for_address(address: str) -> dict:
    return get_weather_for_location(address)
