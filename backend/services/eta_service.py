import logging
import time
from datetime import datetime, timedelta

from core.config import settings

logger = logging.getLogger(__name__)


def _weather_factor(weather: str | None) -> float:
    return settings.WEATHER_FACTOR.get(weather or "Cerah", 1.0)


def calibrate_eta_minutes(
    duration_s: float,
    traffic: str,
    weather: str = "Cerah",
) -> float:
    traffic_factor = settings.TRAFFIC_FACTOR.get(traffic, 1.0)
    return max(duration_s * traffic_factor * _weather_factor(weather) / 60.0, 1.0)


def _fallback_eta_minutes(distance_m: float, traffic: str, weather: str) -> float:
    baseline_seconds = max(distance_m, 0.0) / (30.0 / 3.6)
    return max(
        baseline_seconds * settings.TRAFFIC_FACTOR.get(traffic, 1.0) * _weather_factor(weather) / 60.0,
        1.0,
    )


def _leg_eta(duration_s, distance_m, traffic, weather):
    if duration_s and duration_s > 0:
        return calibrate_eta_minutes(duration_s, traffic, weather), "ors"
    return _fallback_eta_minutes(distance_m, traffic, weather), "haversine"


def build_eta_timestamps(
    route_order: list[int],
    coordinates: list[dict],
    distance_matrix: list[list[float]],
    duration_matrix: list[list[float]],
    traffic: str,
    weather_list: list[dict],
    start_hour: int = 9,
    start_minute: int = 0,
) -> dict:
    started = time.time()
    current = datetime.now().replace(
        hour=start_hour,
        minute=start_minute,
        second=0,
        microsecond=0,
    )
    eta_list = []
    cumulative_distance = 0.0
    cumulative_duration = 0.0

    for stop_number, node in enumerate(route_order[1:-1], start=1):
        previous = route_order[stop_number - 1]
        distance_m = float(distance_matrix[previous][node])
        duration_s = float(duration_matrix[previous][node])
        weather = weather_list[node - 1] if node > 0 else {}
        weather_name = weather.get("weather", "Cerah")
        minutes, source = _leg_eta(duration_s, distance_m, traffic, weather_name)
        current += timedelta(minutes=minutes)
        cumulative_distance += distance_m
        cumulative_duration += minutes * 60
        eta_list.append(
            {
                "stop": stop_number,
                "order_index": node,
                "eta": current.strftime("%H:%M"),
                "eta_date": current.strftime("%Y-%m-%d"),
                "eta_timestamp": current.isoformat(timespec="seconds"),
                "weather": weather_name,
                "temperature": weather.get("temperature", 30),
                "weather_source": weather.get("source", "fallback"),
                "distance_m": round(distance_m, 0),
                "duration_s": round(minutes * 60, 0),
                "cumulative_distance_m": round(cumulative_distance, 0),
                "cumulative_duration_s": round(cumulative_duration, 0),
                "duration_source": source,
            }
        )

    return_leg = None
    if len(route_order) >= 2 and route_order[-1] == 0 and route_order[-2] != 0:
        previous = route_order[-2]
        distance_m = float(distance_matrix[previous][0])
        duration_s = float(duration_matrix[previous][0])
        weather = weather_list[previous - 1] if previous > 0 else {}
        weather_name = weather.get("weather", "Cerah")
        minutes, source = _leg_eta(duration_s, distance_m, traffic, weather_name)
        current += timedelta(minutes=minutes)
        cumulative_distance += distance_m
        cumulative_duration += minutes * 60
        return_leg = {
            "from_index": previous,
            "to_index": 0,
            "eta": current.strftime("%H:%M"),
            "eta_date": current.strftime("%Y-%m-%d"),
            "eta_timestamp": current.isoformat(timespec="seconds"),
            "weather": weather_name,
            "temperature": weather.get("temperature", 30),
            "distance_m": round(distance_m, 0),
            "duration_s": round(minutes * 60, 0),
            "cumulative_distance_m": round(cumulative_distance, 0),
            "cumulative_duration_s": round(cumulative_duration, 0),
            "duration_source": source,
        }

    logger.info("ETA disusun dalam %.0f ms", (time.time() - started) * 1000)
    return {"eta_list": eta_list, "return_leg": return_leg}
