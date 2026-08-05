"""generate_label.py — Tambahkan kolom label fraud ke cod_fraud_synthetic_data.csv.

Aturan labeling (disepakati di SDD):
fraud = 1 jika customer_report == 'Not Received' ATAU
        (customer_report == 'Rejected/Unreachable' DAN gps_distance_m > 1500)
        ATAU (system_status == 'Delivered' DAN customer_report == 'Not Received')
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "cod_fraud_synthetic_data.csv"  # file sumber di root repo
OUT_PATH = ROOT / "data" / "cod_fraud_labeled.csv"


def is_fraud(row: dict) -> int:
    report = (row.get("customer_report") or "").strip()
    status = (row.get("system_status") or "").strip()
    try:
        gps = float(row.get("gps_distance_meters") or 0)
    except ValueError:
        gps = 0.0

    if report == "Not Received":
        return 1
    if report == "Rejected/Unreachable" and gps > 1500:
        return 1
    if status == "Delivered" and report == "Not Received":
        return 1
    return 0


def main():
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    labeled = []
    for r in rows:
        r["fraud"] = str(is_fraud(r))
        labeled.append(r)

    fieldnames = list(rows[0].keys()) + ["fraud"]
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(labeled)

    n_fraud = sum(1 for r in labeled if r["fraud"] == "1")
    print(f"OK: {len(labeled)} baris dilabeli. Fraud: {n_fraud} ({n_fraud/len(labeled):.1%})")


if __name__ == "__main__":
    main()
