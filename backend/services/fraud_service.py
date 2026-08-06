"""Fraud Service — XGBoost Classifier lokal + narasi DeepSeek opsional.

Model dilatih dari cod_fraud_synthetic_data.csv. Jika .pkl belum ada,
pakai aturan heuristik yang meniru pola dataset (gps_distance > 1500m,
item_value > 500k, customer_report != 'Received').
"""
import logging
import pickle

from core.config import settings

logger = logging.getLogger(__name__)

MODEL_PATH = settings.AI_MODELS_DIR / "fraud_model.pkl"

_model = None

FALLBACK_REASON = "WARN: Fraud terdeteksi berdasarkan anomali data. Silakan cek detail di dashboard."


def load_model():
    global _model
    if _model is not None:
        return
    if MODEL_PATH.exists():
        try:
            with open(MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
            logger.info("OK:  Fraud model dimuat dari %s", MODEL_PATH)
            return
        except Exception as exc:
            logger.warning("Gagal load fraud_model.pkl (%s), pakai heuristik.", exc)
    else:
        logger.warning("fraud_model.pkl belum ada — pakai aturan heuristik.")


def _heuristic_score(item_value: float, gps_distance_m: float, customer_report: str) -> float:
    """Skor risiko 0..1 meniru pola training data."""
    score = 0.0
    if customer_report == "Not Received":
        score += 0.55
    elif customer_report in ("Rejected/Unreachable", "Failed"):
        score += 0.25
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
    """Skor probabilitas fraud 0..1."""
    try:
        if _model is not None:
            import pandas as pd

            # Rasio nilai per km jarak (fitur paling penting)
            value_per_km = float(item_value) / max(float(gps_distance_m) / 1000.0, 0.1)

            df = pd.DataFrame(
                [
                    {
                        "item_value": float(item_value),
                        "gps_distance_meters": float(gps_distance_m),
                        "value_per_km": value_per_km,
                        "is_weekend": int(is_weekend),
                        "customer_report_Not Received": int(customer_report == "Not Received"),
                        "customer_report_Received": int(customer_report == "Received"),
                        "customer_report_Rejected/Unreachable": int(
                            customer_report in ("Rejected/Unreachable", "Failed")
                        ),
                        "system_status_Delivered": int(system_status == "Delivered"),
                        "system_status_Failed": int(system_status != "Delivered"),
                    }
                ]
            )
            prob = float(_model.predict_proba(df)[0][1])
            return max(0.0, min(prob, 1.0))
    except Exception as exc:
        logger.warning("Prediksi fraud model gagal (%s), pakai heuristik.", exc)
    return _heuristic_score(item_value, gps_distance_m, customer_report)


def _deepseek_explain(score: float, item_value: float, gps_distance_m: float, customer_report: str) -> str:
    """Narasi fraud dari DeepSeek V4-Flash (opsional)."""
    if not settings.USE_DEEPSEEK or not settings.DEEPSEEK_API_KEY:
        return FALLBACK_REASON
    try:
        import httpx

        prompt = (
            "Anda adalah asisten investigasi logistik. Jelaskan mengapa transaksi ini "
            "terdeteksi fraud, maksimal 2 kalimat dalam Bahasa Indonesia.\n"
            f"- Skor Risiko AI: {score:.0%}\n"
            f"- Laporan Customer: {customer_report}\n"
            f"- Jarak GPS: {gps_distance_m:.0f} meter (normal < 500m)\n"
            f"- Nilai Barang: Rp {item_value:,.0f}\n"
        )
        resp = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 100,
            },
            timeout=settings.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text or FALLBACK_REASON
    except Exception as exc:
        logger.warning("DeepSeek gagal (%s), pakai fallback statis.", exc)
        return FALLBACK_REASON


def analyze_order(
    item_value: float,
    gps_distance_m: float,
    customer_report: str,
    system_status: str = "Delivered",
    is_weekend: int = 0,
) -> dict:
    """Kembalikan dict fraud_alert untuk satu order."""
    score = predict_fraud_score(
        item_value, gps_distance_m, customer_report, system_status, is_weekend
    )
    is_fraud = score >= settings.FRAUD_THRESHOLD
    reason = (
        _deepseek_explain(score, item_value, gps_distance_m, customer_report)
        if is_fraud
        else ""
    )
    return {
        "status": "fraud" if is_fraud else "aman",
        "score": round(score, 4),
        "reason": reason,
        "recommendation": "Freeze Settlement & Investigasi Kurir" if is_fraud else "",
    }
