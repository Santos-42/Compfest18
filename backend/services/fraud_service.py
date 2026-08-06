import json
import logging
import pickle
import re

from core.config import settings

logger = logging.getLogger(__name__)
MODEL_PATH = settings.AI_MODELS_DIR / "fraud_model.pkl"
EXPECTED_FEATURES = [
    "item_value",
    "gps_distance_meters",
    "value_per_km",
    "is_weekend",
    "customer_report_Not Received",
    "customer_report_Received",
    "customer_report_Rejected/Unreachable",
    "system_status_Delivered",
    "system_status_Failed",
]
_model = None
FALLBACK_REASON = "Fraud terdeteksi berdasarkan anomali data. Silakan cek detail di dashboard."


def load_model():
    global _model
    if _model is not None or not MODEL_PATH.exists():
        if not MODEL_PATH.exists():
            logger.warning("fraud_model.pkl tidak ditemukan; menggunakan heuristik")
        return
    try:
        with MODEL_PATH.open("rb") as model_file:
            candidate = pickle.load(model_file)
        feature_names_value = getattr(candidate, "feature_names_in_", None)
        feature_names = list(feature_names_value) if feature_names_value is not None else []
        if feature_names and feature_names != EXPECTED_FEATURES:
            raise ValueError("Feature fraud model tidak sesuai dengan kontrak inferensi.")
        _model = candidate
        logger.info("Fraud model dimuat dari %s", MODEL_PATH)
    except Exception as exc:
        logger.warning("Fraud model gagal dimuat: %s; menggunakan heuristik", exc)


def model_status() -> str:
    return "loaded" if _model is not None else "heuristic"


def _heuristic_score(item_value, gps_distance_m, customer_report, system_status):
    score = 0.0
    if customer_report == "Not Received":
        score += 0.55
    elif customer_report in ("Rejected/Unreachable", "Failed"):
        score += 0.25
    if system_status == "Delivered" and customer_report == "Not Received":
        score += 0.2
    if gps_distance_m > 1500:
        score += 0.3
    elif gps_distance_m > 500:
        score += 0.15
    if item_value > 500_000:
        score += 0.15
    elif item_value > 200_000:
        score += 0.05
    return min(score, 0.99)


def predict_fraud_score(
    item_value: float,
    gps_distance_m: float,
    customer_report: str,
    system_status: str = "Delivered",
    is_weekend: int = 0,
) -> float:
    if _model is not None:
        try:
            import pandas as pd

            value_per_km = float(item_value) / max(float(gps_distance_m) / 1000.0, 0.1)
            frame = pd.DataFrame(
                [{
                    "item_value": float(item_value),
                    "gps_distance_meters": float(gps_distance_m),
                    "value_per_km": value_per_km,
                    "is_weekend": int(is_weekend),
                    "customer_report_Not Received": int(customer_report == "Not Received"),
                    "customer_report_Received": int(customer_report == "Received"),
                    "customer_report_Rejected/Unreachable": int(
                        customer_report == "Rejected/Unreachable"
                    ),
                    "system_status_Delivered": int(system_status == "Delivered"),
                    "system_status_Failed": int(system_status == "Failed"),
                }],
                columns=EXPECTED_FEATURES,
            )
            probability = float(_model.predict_proba(frame)[0][1])
            return max(0.0, min(probability, 1.0))
        except Exception as exc:
            logger.warning("Prediksi fraud model gagal: %s", exc)
    return _heuristic_score(item_value, gps_distance_m, customer_report, system_status)


def analyze_order(
    item_value: float,
    gps_distance_m: float,
    customer_report: str,
    system_status: str = "Delivered",
    is_weekend: int = 0,
    include_explanation: bool = True,
) -> dict:
    score = predict_fraud_score(
        item_value,
        gps_distance_m,
        customer_report,
        system_status,
        is_weekend,
    )
    is_fraud = score >= settings.FRAUD_THRESHOLD
    return {
        "status": "fraud" if is_fraud else "aman",
        "score": round(score, 4),
        "reason": _fallback_reason() if is_fraud and include_explanation else "",
        "recommendation": "Freeze Settlement & Investigasi Kurir" if is_fraud else "",
    }


def _fallback_reason():
    return FALLBACK_REASON


def explain_alerts(alerts: list[dict]) -> list[dict]:
    fraud_alerts = [alert for alert in alerts if alert.get("status") == "fraud"]
    if not fraud_alerts or not settings.USE_DEEPSEEK or not settings.DEEPSEEK_API_KEY:
        return alerts
    try:
        import httpx

        summary = [
            {
                "order_index": alert["order_index"],
                "score": alert["score"],
                "cod_amount": alert["cod_amount"],
                "gps_distance_m": alert["gps_distance_m"],
                "customer_report": alert["customer_report"],
                "system_status": alert["system_status"],
            }
            for alert in fraud_alerts
        ]
        prompt = (
            "Jelaskan setiap transaksi fraud berikut dalam Bahasa Indonesia, maksimal 2 kalimat. "
            "Balas JSON array dengan key order_index dan explanation tanpa markdown. Data: "
            + json.dumps(summary, ensure_ascii=False)
        )
        response = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300,
            },
            timeout=settings.DEEPSEEK_TIMEOUT,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        text = re.sub(r"^```(?:json)?|```$", "", text).strip()
        explanations = {
            int(item["order_index"]): item["explanation"]
            for item in json.loads(text)
            if item.get("explanation")
        }
        for alert in alerts:
            if alert.get("order_index") in explanations:
                alert["reason"] = explanations[alert["order_index"]]
    except Exception as exc:
        logger.warning("DeepSeek batch gagal: %s", exc)
    return alerts
