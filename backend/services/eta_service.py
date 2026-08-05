"""ETA Service — XGBoost Regressor lokal + penyesuaian trafik/cuaca.

Fallback: model baseline sederhana (jarak/kecepatan + faktor) jika model belum
dilatih / file .pkl tidak ada.
"""
import logging
import pickle
import time
from datetime import datetime, timedelta

from core.config import settings

logger = logging.getLogger(__name__)

MODEL_PATH = settings.AI_MODELS_DIR / "eta_model.pkl"

_model = None


def load_model():
    global _model
    if _model is not None:
        return
    if MODEL_PATH.exists():
        try:
            with open(MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
            logger.info("OK:  ETA model dimuat dari %s", MODEL_PATH)
            return
        except Exception as exc:
            logger.warning("Gagal load eta_model.pkl (%s), pakai fallback.", exc)
    else:
        logger.warning("eta_model.pkl belum ada — pakai fallback baseline.")


def _eta_minutes(distance_m: float, traffic: str, weather: str) -> float:
    """Fallback baseline: 30 km/jam * faktor trafik & cuaca."""
    speed = 30.0 / 3.6  # m/s
    base = distance_m / speed if distance_m > 0 else 0.0
    base *= settings.TRAFFIC_FACTOR.get(traffic, 1.0)
    base *= settings.WEATHER_FACTOR.get(weather, 1.0)
    return base / 60.0


def predict_eta_minutes(
    distance_m: float,
    traffic: str,
    weather: str,
    is_last_stop: bool = False,
) -> float:
    """Prediksi durasi antar dua titik (menit)."""
    try:
        if _model is not None:
            import numpy as np
            import pandas as pd

            df = pd.DataFrame(
                [
                    {
                        "distance_m": float(distance_m),
                        "traffic_factor": settings.TRAFFIC_FACTOR.get(traffic, 1.0),
                        "weather_factor": settings.WEATHER_FACTOR.get(weather, 1.0),
                        "is_last_stop": int(is_last_stop),
                    }
                ]
            )
            pred = float(_model.predict(df)[0])
            return max(pred, 1.0)
    except Exception as exc:
        logger.warning("Prediksi ETA model gagal (%s), pakai baseline.", exc)
    return max(_eta_minutes(distance_m, traffic, weather), 1.0)


def build_eta_timestamps(
    route_order: list[int],
    coordinates: list[dict],
    duration_matrix: list[list[float]],
    traffic: str,
    weather_list: list[dict],
    start_hour: int = 9,
    start_minute: int = 0,
) -> list[dict]:
    """Susun ETA kumulatif per stop berdasarkan urutan rute.

    route_order: [0, 2, 1, 3, ...] (indeks asli), weather_list sejajar indeks asli.
    """
    eta_list = []
    current = datetime.now().replace(
        hour=start_hour, minute=start_minute, second=0, microsecond=0
    )
    current_time = time.time()
    for k, node in enumerate(route_order):
        if k == 0:
            # Origin tidak dihitung sebagai stop; mulai dari stop pertama
            continue
        prev = route_order[k - 1]
        dur_s = duration_matrix[prev][node]
        weather = weather_list[node - 1].get("weather", "Cerah")  # weather_list tanpa origin
        minutes = predict_eta_minutes(
            dur_s * 1000.0 / 1000.0,  # sudah meter
            traffic,
            weather,
            is_last_stop=(k == len(route_order) - 1),
        )
        current += timedelta(minutes=minutes)
        eta_list.append(
            {
                "stop": k,  # 1-based urutan pengiriman
                "order_index": node,  # indeks asli input
                "eta": current.strftime("%H:%M"),
                "eta_timestamp": current.isoformat(timespec="seconds"),
                "weather": weather,
                "temperature": weather_list[node - 1].get("temperature", 30),
            }
        )
    logger.info("ETA disusun dalam %.0f ms", (time.time() - current_time) * 1000)
    return eta_list
