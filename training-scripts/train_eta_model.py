"""train_eta_model.py — Latih XGBoost Regressor untuk prediksi durasi (menit).

Data sintetis: durasi = jarak / kecepatan_efektif * faktor trafik * faktor cuaca + noise.
Fitur: distance_m, traffic_factor, weather_factor, is_last_stop.
"""
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "ai-models" / "eta_model.pkl"

TRAFFIC_FACTORS = {"normal": 1.0, "congested": 1.55, "hujan": 1.25}
WEATHER_FACTORS = {
    "Cerah": 1.0, "Cerah Berawan": 1.05, "Berawan": 1.1, "Berawan Tebal": 1.15,
    "Udara Kabur": 1.15, "Asap": 1.15, "Kabut": 1.2, "Hujan Ringan": 1.25,
    "Hujan Sedang": 1.4, "Hujan Lokal": 1.4, "Hujan Lebat": 1.6,
    "Petir": 1.6, "Petir Disertai Hujan": 1.6,
}


def synthetic_dataset(n=5000, seed=42):
    rng = np.random.default_rng(seed)
    distance_m = rng.uniform(500, 40_000, n)
    traffic = rng.choice(list(TRAFFIC_FACTORS), n)
    weather = rng.choice(list(WEATHER_FACTORS), n)
    is_last = rng.integers(0, 2, n)

    traffic_f = np.array([TRAFFIC_FACTORS[t] for t in traffic])
    weather_f = np.array([WEATHER_FACTORS[w] for w in weather])
    speed_ms = 30.0 / 3.6  # 30 km/jam baseline

    eta_min = distance_m / speed_ms / 60.0 * traffic_f * weather_f
    eta_min *= 1 + 0.12 * (is_last - 0.5)  # stop terakhir sedikit lebih lambat
    eta_min += rng.normal(0, 1.5, n).clip(-3, 3)

    return pd.DataFrame(
        {
            "distance_m": distance_m,
            "traffic_factor": traffic_f,
            "weather_factor": weather_f,
            "is_last_stop": is_last,
            "eta_min": eta_min.clip(1),
        }
    )


def main():
    df = synthetic_dataset()
    X = df[["distance_m", "traffic_factor", "weather_factor", "is_last_stop"]]
    y = df["eta_min"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"OK: MAE ETA: {mae:.2f} menit")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"OK: eta_model.pkl disimpan ke {OUT_PATH}")


if __name__ == "__main__":
    main()
