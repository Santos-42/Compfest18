"""train_fraud_model.py — Latih XGBoost Classifier dari CSV berlabel, simpan fraud_model.pkl.

Fitur: item_value, gps_distance_meters, customer_report one-hot,
value_per_km (nilai/jarak), is_weekend (pola penipuan akhir pekan).
"""
import pickle
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

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

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "cod_fraud_labeled.csv"
OUT_PATH = ROOT / "ai-models" / "fraud_model.pkl"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Fitur turunan dari data mentah."""
    df = df.copy()
    df["fraud"] = df["fraud"].astype(int)
    df["item_value"] = df["item_value"].astype(float)
    df["gps_distance_meters"] = df["gps_distance_meters"].astype(float)

    # Rasio nilai per km jarak: nilai tinggi + jarak pendek = anomali
    df["value_per_km"] = df["item_value"] / (df["gps_distance_meters"] / 1000.0).clip(lower=0.1)

    # Akhir pekan (Sabtu/Minggu) — pola penipuan
    df["delivery_date"] = pd.to_datetime(df["delivery_date"], errors="coerce")
    df["is_weekend"] = df["delivery_date"].dt.dayofweek.isin([5, 6]).astype(int)

    # One-hot customer_report + system_status
    report_dummies = pd.get_dummies(df["customer_report"], prefix="customer_report")
    status_dummies = pd.get_dummies(df["system_status"], prefix="system_status")

    features = pd.concat(
        [
            df[["item_value", "gps_distance_meters", "value_per_km", "is_weekend"]],
            report_dummies,
            status_dummies,
        ],
        axis=1,
    )
    # Pastikan kolom konsisten dengan inferensi
    for col in [
        "customer_report_Not Received",
        "customer_report_Received",
        "customer_report_Rejected/Unreachable",
        "system_status_Delivered",
        "system_status_Failed",
    ]:
        if col not in features.columns:
            features[col] = 0
    features = features.reindex(columns=EXPECTED_FEATURES, fill_value=0)
    return features


def main():
    df = pd.read_csv(CSV_PATH)
    X = build_features(df)
    y = df["fraud"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=250,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["Aman", "Fraud"]))

    # Feature importance
    imp = sorted(
        zip(X.columns, model.feature_importances_),
        key=lambda x: -x[1],
    )
    print("\nFeature importance:")
    for name, v in imp[:10]:
        print(f"  {name}: {v:.3f}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"\nOK: fraud_model.pkl disimpan ke {OUT_PATH}")


if __name__ == "__main__":
    main()
