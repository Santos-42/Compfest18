"""generate_label.py — Tambahkan kolom label fraud ke cod_fraud_synthetic_data.csv.

Aturan labeling berada di `fraud_label_rules.py` dan dipakai bersama oleh seluruh script training.
"""
import csv
from pathlib import Path

from fraud_label_rules import is_fraud

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "cod_fraud_synthetic_data.csv"  # file sumber di root repo
OUT_PATH = ROOT / "data" / "cod_fraud_labeled.csv"


def main():
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    labeled = []
    for r in rows:
        r["fraud"] = str(is_fraud(r))
        labeled.append(r)

    fieldnames = list(rows[0].keys())
    if len(fieldnames) != len(set(fieldnames)):
        raise ValueError("Header CSV memiliki kolom duplikat.")
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(labeled)

    n_fraud = sum(1 for r in labeled if r["fraud"] == "1")
    print(f"OK: {len(labeled)} baris dilabeli. Fraud: {n_fraud} ({n_fraud/len(labeled):.1%})")


if __name__ == "__main__":
    main()
