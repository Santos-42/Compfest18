"""train_fraud_model.py — Latih XGBoost Classifier dari CSV berlabel, simpan fraud_model.pkl.

Fitur: item_value, gps_distance_m, one-hot customer_report.
"""
import pickle
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "cod_fraud_labeled.csv"
OUT_PATH = ROOT / "ai-models" / "fraud_model.pkl"


def main():
    df = pd.read_csv(CSV_PATH)
    df["fraud"] = df["fraud"].astype(int)

    features = pd.get_dummies(
        df[["item_value", "gps_distance_meters", "customer_report"]],
        columns=["customer_report"],
        prefix="customer_report",
    )
    # Pastikan kolom one-hot konsisten dengan inferensi
    for col in ["customer_report_Not Received", "customer_report_Rejected/Unreachable"]:
        if col not in features.columns:
            features[col] = 0

    X = features
    y = df["fraud"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["Aman", "Fraud"]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"OK: fraud_model.pkl disimpan ke {OUT_PATH}")


if __name__ == "__main__":
    main()
