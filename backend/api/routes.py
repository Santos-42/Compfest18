"""REST API routes — POST /api/run-simulation."""
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.database import save_simulation
from services import (
    directions_service,
    distance_service,
    eta_service,
    fraud_service,
    geocoding_service,
    routing_service,
    weather_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["simulation"])

ORIGIN_LAT = -6.2
ORIGIN_LNG = 106.816666


class SimulationRequest(BaseModel):
    addresses: list[str] = Field(..., min_length=1)
    cod_amounts: Optional[list[float]] = None
    traffic_condition: str = "normal"


class SimulationResponse(BaseModel):
    status: str
    route: dict
    polyline: str
    eta_list: list[dict]
    fraud_alerts: list[dict]
    processing_time_ms: int


def _parse_cod(amounts: Optional[list[float]], n: int) -> list[float]:
    """Normalisasi cod_amounts: isi None / kurang dengan nilai acak deterministik."""
    import random

    if not amounts:
        return [round(random.uniform(50_000, 750_000), 0) for _ in range(n)]
    out = []
    rnd = random.Random(42)
    for i in range(n):
        val = amounts[i] if i < len(amounts) and amounts[i] is not None else rnd.uniform(50_000, 750_000)
        out.append(float(val))
    return out


@router.post("/run-simulation", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    start = time.time()
    n = len(req.addresses)
    if n > 15:
        raise HTTPException(status_code=400, detail="Maksimal 15 alamat per simulasi.")

    traffic = req.traffic_condition if req.traffic_condition in ("normal", "congested") else "normal"
    cod_amounts = _parse_cod(req.cod_amounts, n)

    # 1. Geocoding
    try:
        points = [geocoding_service.geocode(a) for a in req.addresses]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding gagal: {exc}")
    origin = {"lat": ORIGIN_LAT, "lng": ORIGIN_LNG}
    all_points = [origin] + points  # index 0 = gudang

    # 2. Cuaca per titik (parallelize sederhana)
    weather_list = [weather_service.get_weather_for_address(a) for a in req.addresses]

    # 3. Distance matrix (n+1 x n+1)
    distances, durations = distance_service.get_distance_matrix(all_points)

    # 4. Routing OR-Tools
    route_order = routing_service.optimize_route(distances)  # [0, ...stops]

    # 5. ETA
    eta_list = eta_service.build_eta_timestamps(
        route_order, all_points, durations, traffic, weather_list
    )

    # 6. Fraud detection per stop (nominal acak bila tidak diisi)
    fraud_alerts = []
    for idx, node in enumerate(route_order):
        if node == 0:
            continue
        stop_index = node  # indeks asli input
        gps_dist = distances[0][node]  # jarak gudang -> stop
        item_value = cod_amounts[stop_index - 1] if stop_index > 0 else 0.0
        report = "Not Received" if (gps_dist > 1500 and item_value > 500_000) else "Received"
        result = fraud_service.analyze_order(item_value, gps_dist, report)
        fraud_alerts.append(
            {
                "order_index": stop_index,
                "address": req.addresses[stop_index - 1],
                "cod_amount": item_value,
                "gps_distance_m": round(gps_dist, 0),
                "customer_report": report,
                **result,
            }
        )

    # 7. Polyline (urutan rute)
    ordered_coords = [(all_points[i]["lat"], all_points[i]["lng"]) for i in route_order]
    polyline = directions_service.get_polyline(ordered_coords)

    response = {
        "status": "success",
        "route": {
            "order": route_order,
            "coordinates": [[p["lng"], p["lat"]] for p in all_points],
        },
        "polyline": polyline,
        "eta_list": eta_list,
        "fraud_alerts": fraud_alerts,
        "processing_time_ms": int((time.time() - start) * 1000),
    }

    try:
        save_simulation(req.addresses, response)
    except Exception as exc:
        logger.warning("Gagal simpan history: %s", exc)

    return response


@router.get("/health")
def health():
    return {"status": "ok"}
