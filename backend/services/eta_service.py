"""ETA Service — durasi ORS langsung + kalibrasi kondisi lalu lintas.

Strategi: durasi antar titik dari ORS Matrix (detik) sudah memperhitungkan
jalan & kecepatan aktual. Kita kalibrasi dengan faktor kondisi lalu lintas
(normal/macet/hujan). Fallback: Haversine 30 km/jam bila durasi ORS tak ada.
"""
import logging
import time
from datetime import datetime, timedelta

from core.config import settings

logger = logging.getLogger(__name__)

# Kalibrasi kondisi lalu lintas terhadap durasi ORS baseline.
# ORS duration mengasumsikan kondisi normal; macet/hujan menambah waktu.
TRAFFIC_MULTIPLIER = {
    "normal": 1.0,
    "congested": 1.55,
    "hujan": 1.35,
}


def calibrate_eta_minutes(duration_s: float, traffic: str) -> float:
    """Durasi ORS (detik) -> menit terkoreksi kondisi lalu lintas."""
    mult = TRAFFIC_MULTIPLIER.get(traffic, 1.0)
    return max(duration_s * mult / 60.0, 1.0)


def _fallback_eta_minutes(distance_m: float, traffic: str) -> float:
    """Fallback bila durasi ORS tidak tersedia: 30 km/jam * faktor trafik."""
    speed = 30.0 / 3.6  # m/s
    base = distance_m / speed if distance_m > 0 else 0.0
    base *= TRAFFIC_MULTIPLIER.get(traffic, 1.0)
    return max(base / 60.0, 1.0)


def build_eta_timestamps(
    route_order: list[int],
    coordinates: list[dict],
    distance_matrix: list[list[float]],
    duration_matrix: list[list[float]],
    traffic: str,
    weather_list: list[dict],
    start_hour: int = 9,
    start_minute: int = 0,
) -> list[dict]:
    """Susun ETA kumulatif per stop berdasarkan urutan rute.

    route_order: [0, 2, 1, 3, ...] (indeks asli), weather_list sejajar indeks asli.
    distance_matrix: jarak antar titik (meter) — fallback.
    duration_matrix: durasi antar titik dari ORS (detik) — sumber utama.
    """
    eta_list = []
    current = datetime.now().replace(
        hour=start_hour, minute=start_minute, second=0, microsecond=0
    )
    cumulative_m = 0.0
    current_time = time.time()
    for k, node in enumerate(route_order):
        if k == 0:
            # Origin tidak dihitung sebagai stop; mulai dari stop pertama
            continue
        prev = route_order[k - 1]
        dist_m = distance_matrix[prev][node]
        dur_s = duration_matrix[prev][node]
        weather = weather_list[node - 1].get("weather", "Cerah")  # weather_list tanpa origin
        if dur_s and dur_s > 0:
            minutes = calibrate_eta_minutes(dur_s, traffic)
        else:
            minutes = _fallback_eta_minutes(dist_m, traffic)
        current += timedelta(minutes=minutes)
        cumulative_m += dist_m
        eta_list.append(
            {
                "stop": k,  # 1-based urutan pengiriman
                "order_index": node,  # indeks asli input
                "eta": current.strftime("%H:%M"),
                "eta_timestamp": current.isoformat(timespec="seconds"),
                "weather": weather,
                "temperature": weather_list[node - 1].get("temperature", 30),
                "distance_m": round(dist_m, 0),  # jarak segmen (m)
                "cumulative_distance_m": round(cumulative_m, 0),  # total dari gudang (m)
            }
        )
    logger.info("ETA disusun dalam %.0f ms", (time.time() - current_time) * 1000)
    return eta_list
