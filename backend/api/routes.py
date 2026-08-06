"""REST API routes for simulation and address suggestions."""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from core.config import settings
from core.database import DB_PATH, save_simulation
from services import (
    directions_service,
    distance_service,
    eta_service,
    fraud_service,
    geocoding_service,
    routing_service,
    suggest_service,
    weather_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["simulation"])


class TrafficCondition(str, Enum):
    normal = "normal"
    congested = "congested"
    hujan = "hujan"


class OptimizationMode(str, Enum):
    distance = "distance"
    time = "time"


class CustomerReport(str, Enum):
    received = "Received"
    not_received = "Not Received"
    rejected = "Rejected/Unreachable"


class SystemStatus(str, Enum):
    delivered = "Delivered"
    failed = "Failed"


class AddressInput(BaseModel):
    address: str = Field(..., min_length=3, max_length=300)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    cod_amount: Optional[float] = Field(default=None, ge=0, le=100_000_000_000)
    customer_report: Optional[CustomerReport] = None
    system_status: Optional[SystemStatus] = None
    adm4_code: Optional[str] = Field(default=None, min_length=1, max_length=32)
    adm2_code: Optional[str] = Field(default=None, min_length=1, max_length=32)
    district: Optional[str] = Field(default=None, max_length=150)
    city: Optional[str] = Field(default=None, max_length=150)
    county: Optional[str] = Field(default=None, max_length=150)
    state: Optional[str] = Field(default=None, max_length=150)
    locality: Optional[str] = Field(default=None, max_length=150)

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat dan lng harus dikirim berpasangan.")
        return self


class SimulationRequest(BaseModel):
    addresses: list[AddressInput] = Field(..., min_length=1, max_length=15)
    traffic_condition: TrafficCondition = TrafficCondition.normal
    optimization: OptimizationMode = OptimizationMode.distance
    demo_mode: bool = True
    simulation_seed: int = Field(default=42, ge=0, le=2_147_483_647)

    @model_validator(mode="after")
    def validate_transaction_fields(self):
        if not self.demo_mode:
            missing = []
            for index, address in enumerate(self.addresses):
                fields = []
                if address.cod_amount is None:
                    fields.append("cod_amount")
                if address.customer_report is None:
                    fields.append("customer_report")
                if address.system_status is None:
                    fields.append("system_status")
                if fields:
                    missing.append({"index": index, "fields": fields})
            if missing:
                raise ValueError(
                    "Mode normal memerlukan data transaksi lengkap untuk setiap alamat: "
                    + str(missing)
                )
        return self


class SimulationResponse(BaseModel):
    status: str
    route: dict
    polyline: str
    locations: list[dict]
    eta_list: list[dict]
    return_leg: Optional[dict]
    fraud_alerts: list[dict]
    warnings: list[str]
    simulation: dict
    processing_time_ms: int


def _parallel_map(function, values):
    results = [None] * len(values)
    errors = []
    worker_count = min(4, max(1, len(values)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(function, value): index for index, value in enumerate(values)}
        for future in as_completed(futures):
            index = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                errors.append((index, exc))
    return results, errors


def _location_metadata(address: AddressInput) -> dict:
    return {
        key: value
        for key, value in {
            "adm4_code": address.adm4_code,
            "adm2_code": address.adm2_code,
            "district": address.district,
            "city": address.city,
            "county": address.county,
            "state": address.state,
            "locality": address.locality,
        }.items()
        if value is not None
    }


def _geocode_address(address: AddressInput, allow_mock: bool = False) -> dict:
    if address.lat is not None and address.lng is not None:
        result = {
            "lat": address.lat,
            "lng": address.lng,
            "source": "autocomplete",
            "confidence": 1.0,
            "is_fallback": False,
        }
        result.update(_location_metadata(address))
        return result
    return geocoding_service.geocode(address.address, allow_mock=allow_mock)


def _demo_transactions(addresses: list[AddressInput], seed: int) -> list[dict]:
    import random

    generator = random.Random(seed)
    patterns = [
        ("Received", "Delivered"),
        ("Not Received", "Delivered"),
        ("Rejected/Unreachable", "Failed"),
    ]
    transactions = []
    for index, _address in enumerate(addresses):
        report, status = patterns[generator.randrange(len(patterns))]
        transactions.append(
            {
                "cod_amount": float(generator.randrange(100, 1_501) * 1_000),
                "customer_report": report,
                "system_status": status,
                "source": "demo",
                "input_index": index + 1,
            }
        )
    return transactions


def _request_transactions(req: SimulationRequest) -> tuple[list[dict], dict]:
    if req.demo_mode:
        transactions = _demo_transactions(req.addresses, req.simulation_seed)
        return transactions, {
            "demo_mode": True,
            "seed": req.simulation_seed,
            "generated_transaction_fields": True,
        }
    return [
        {
            "cod_amount": address.cod_amount,
            "customer_report": address.customer_report.value,
            "system_status": address.system_status.value,
            "source": "request",
            "input_index": index + 1,
        }
        for index, address in enumerate(req.addresses)
    ], {"demo_mode": False, "seed": None, "generated_transaction_fields": False}


def _error_details(errors, addresses):
    return [
        {
            "index": index,
            "address": addresses[index].address,
            "message": str(error),
        }
        for index, error in errors
    ]


@router.post("/run-simulation", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    started = time.monotonic()
    transactions, simulation = _request_transactions(req)
    warnings = []
    if req.demo_mode:
        warnings.append(
            "Mode Simulasi aktif: nominal COD, laporan customer, dan status pengiriman dibuat deterministik dari seed."
        )

    points, geocode_errors = _parallel_map(
        lambda address: _geocode_address(address, allow_mock=req.demo_mode),
        req.addresses,
    )
    if geocode_errors:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Satu atau lebih alamat tidak dapat diverifikasi.",
                "errors": _error_details(geocode_errors, req.addresses),
            },
        )
    for index, point in enumerate(points):
        if point.get("is_fallback"):
            warnings.append(
                f"Alamat #{index + 1} menggunakan koordinat mock dan tidak terverifikasi."
            )

    weather_list, weather_errors = _parallel_map(
        lambda address_and_point: weather_service.get_weather_for_location(
            address_and_point[0].address,
            address_and_point[1],
        ),
        list(zip(req.addresses, points)),
    )
    if weather_errors:
        if not settings.ENABLE_FALLBACK:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Data cuaca tidak dapat diperoleh.",
                    "errors": _error_details(weather_errors, req.addresses),
                },
            )
        for index, _error in weather_errors:
            weather_list[index] = {
                "weather": "Cerah",
                "temperature": 30,
                "adm4_code": None,
                "source": "fallback",
                "is_fallback": True,
            }
    for index, weather in enumerate(weather_list):
        if weather.get("is_fallback"):
            warnings.append(f"Cuaca alamat #{index + 1} menggunakan fallback.")

    origin = {
        "lat": settings.ORIGIN_LAT,
        "lng": settings.ORIGIN_LNG,
        "source": "origin",
        "confidence": 1.0,
        "is_fallback": False,
    }
    all_points = [origin] + points
    distances, durations = distance_service.get_distance_matrix(all_points)
    route_order = routing_service.optimize_route(
        distances,
        durations,
        req.optimization.value,
    )
    eta_payload = eta_service.build_eta_timestamps(
        route_order,
        all_points,
        distances,
        durations,
        req.traffic_condition.value,
        weather_list,
    )
    eta_list = eta_payload["eta_list"]
    return_leg = eta_payload["return_leg"]
    if any(item.get("duration_source") == "haversine" for item in eta_list) or (
        return_leg and return_leg.get("duration_source") == "haversine"
    ):
        warnings.append("Sebagian ETA menggunakan fallback Haversine, bukan durasi jalan ORS.")

    is_weekend = 1 if time.localtime().tm_wday >= 5 else 0
    fraud_alerts = []
    for node in route_order[1:-1]:
        input_index = node - 1
        transaction = transactions[input_index]
        gps_distance = distances[0][node]
        result = fraud_service.analyze_order(
            transaction["cod_amount"],
            gps_distance,
            transaction["customer_report"],
            transaction["system_status"],
            is_weekend,
            include_explanation=False,
        )
        fraud_alerts.append(
            {
                "order_index": node,
                "address": req.addresses[input_index].address,
                "cod_amount": transaction["cod_amount"],
                "gps_distance_m": round(gps_distance, 0),
                "customer_report": transaction["customer_report"],
                "system_status": transaction["system_status"],
                **result,
            }
        )
    fraud_alerts = fraud_service.explain_alerts(fraud_alerts)

    ordered_coordinates = [
        [all_points[index]["lng"], all_points[index]["lat"]]
        for index in route_order
    ]
    polyline = directions_service.get_polyline(
        [(coordinate[1], coordinate[0]) for coordinate in ordered_coordinates]
    )
    route = {
        "order": route_order,
        "closed": True,
        "coordinates": [[point["lng"], point["lat"]] for point in all_points],
        "ordered_coordinates": ordered_coordinates,
        "total_distance_m": round(routing_service.route_totals(route_order, distances), 0),
        "total_duration_s": round(routing_service.route_totals(route_order, durations), 0),
    }
    locations = [
        {
            "input_index": index + 1,
            "address": address.address,
            **{
                key: value
                for key, value in point.items()
                if key not in {"lat", "lng"}
            },
            "lat": point["lat"],
            "lng": point["lng"],
            "weather": weather_list[index],
        }
        for index, (address, point) in enumerate(zip(req.addresses, points))
    ]
    if time.monotonic() - started > settings.TOTAL_TIMEOUT:
        raise HTTPException(status_code=504, detail="Batas waktu simulasi terlampaui.")

    response = {
        "status": "success",
        "route": route,
        "polyline": polyline,
        "locations": locations,
        "eta_list": eta_list,
        "return_leg": return_leg,
        "fraud_alerts": fraud_alerts,
        "warnings": warnings,
        "simulation": simulation,
        "processing_time_ms": int((time.monotonic() - started) * 1000),
    }
    try:
        save_simulation(
            [address.model_dump(mode="json") for address in req.addresses],
            response,
        )
    except Exception as exc:
        logger.warning("Gagal menyimpan history: %s", exc)
    return response


@router.get("/geosuggest")
def geosuggest(q: str = "", limit: int = 6):
    return {"query": q, "results": suggest_service.suggest(q, limit=min(max(limit, 1), 10))}


@router.get("/health")
def health():
    return {
        "status": "ok",
        "database": DB_PATH.exists(),
        "fraud_model": fraud_service.model_status(),
        "mock_mode": settings.USE_MOCK_MODE,
    }
