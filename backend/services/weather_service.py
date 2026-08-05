"""Weather Service — BMKG API (data.bmkg.go.id) dengan fallback 'Cerah'."""
import logging

import httpx

from core.config import settings
from core.database import find_adm2_from_address, find_adm4_from_address

logger = logging.getLogger(__name__)

BMKG_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"

DEFAULT_WEATHER = "Cerah"
DEFAULT_TEMP = 30


def _extract_weather(data: dict) -> tuple[str, float]:
    """Parse respons BMKG -> (deskripsi cuaca, suhu).

    Struktur asli: {"lokasi": {...}, "data": [{"lokasi":..., "cuaca": [
        {"datetime":..., "t": 19, "weather": 2, "weather_desc": "Cerah Berawan", ...}
    ]}]}
    """
    try:
        forecast_list = data["data"][0]["cuaca"]
        for item in forecast_list:
            if not isinstance(item, dict):
                continue
            desc = item.get("weather_desc")
            if desc:
                temp = item.get("t", DEFAULT_TEMP)
                try:
                    temp = float(temp)
                except (TypeError, ValueError):
                    temp = DEFAULT_TEMP
                return str(desc), temp
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        logger.warning("Parsing BMKG gagal: %s", exc)
    return DEFAULT_WEATHER, DEFAULT_TEMP


def get_weather_for_address(address: str) -> dict:
    """Cuaca untuk sebuah alamat. Cari kode adm4 (atau fallback adm2) dari
    wilayah.sql, query BMKG; fallback 'Cerah' 30°C jika API gagal."""
    if settings.USE_MOCK_MODE:
        return {"weather": DEFAULT_WEATHER, "temperature": DEFAULT_TEMP}

    adm4 = find_adm4_from_address(address)
    kode = adm4 or find_adm2_from_address(address)
    if not kode:
        return {"weather": DEFAULT_WEATHER, "temperature": DEFAULT_TEMP}

    try:
        resp = httpx.get(
            BMKG_URL, params={"adm4": kode}, timeout=settings.REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        weather, temp = _extract_weather(resp.json())
        return {"weather": weather, "temperature": temp}
    except Exception as exc:
        logger.warning("BMKG API gagal (%s), fallback cuaca default.", exc)

    if settings.ENABLE_FALLBACK:
        return {"weather": DEFAULT_WEATHER, "temperature": DEFAULT_TEMP}
    raise RuntimeError(f"Cuaca gagal diperoleh untuk: {address}")
