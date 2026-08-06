"""enrich_fraud_data.py — Perkaya data fraud sintetis dengan pola realistis.

Data asli terlalu sederhana (fraud hanya = Not Received). Ditambah pola:
1. Received + jarak sangat jauh (>5km) + nilai tinggi (>750rb) -> fraud
   (kurir mengaku diterima tapi lokasi jauh = anomali)
2. Rejected/Unreachable + jarak jauh (>1500m) -> fraud
3. Received + jarak jauh + nilai rendah -> AMAN (baseline)
4. Received + jarak normal + nilai tinggi -> AMAN

Output: data/cod_fraud_labeled.csv (dengan kolom fraud).
"""
import csv
import random
from pathlib import Path

from fraud_label_rules import is_fraud

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "cod_fraud_synthetic_data.csv"
OUT_PATH = ROOT / "data" / "cod_fraud_labeled.csv"

random.seed(42)

CITIES = [
    "Jakarta", "Bandung", "Surabaya", "Medan", "Semarang", "Makassar",
    "Palembang", "Depok", "Bekasi", "Tangerang", "Bogor", "Yogyakarta",
    "Malang", "Padang", "Balikpapan", "Pekanbaru", "Denpasar", "Lampung",
]
NAMES = [
    "Budi Santoso", "Siti Rahayu", "Agus Wijaya", "Dewi Lestari", "Rudi Hartono",
    "Maya Sari", "Joko Susilo", "Rina Wulandari", "Andi Pratama", "Lina Marlina",
]
COURIERS = ["Asmuni Rajata", "Cakrawala Fujiati", "Darmawan Nugroho", "Eko Prasetyo"]


def _row(order_id, value, gps, report, status):
    return {
        "order_id": order_id,
        "courier_name": random.choice(COURIERS),
        "customer_name": random.choice(NAMES),
        "customer_city": random.choice(CITIES),
        "payment_method": "COD",
        "item_value": value,
        "system_status": status,
        "customer_report": report,
        "gps_distance_meters": gps,
        "delivery_date": f"2026-{random.randint(6, 7):02d}-{random.randint(1, 28):02d}",
    }


def main():
    with open(SRC_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    extra = []
    order_counter = len(rows) + 1

    # 1. Received + jarak jauh (>5km) + nilai tinggi -> fraud
    for i in range(150):
        extra.append(
            _row(
                f"ORD-ENRICH-{order_counter + i:05d}",
                random.randint(800_000, 1_500_000),
                random.randint(5_000, 20_000),
                "Received",
                "Delivered",
            )
        )
    order_counter += 150

    # 2. Received + jarak jauh + nilai rendah -> AMAN (pembanding)
    for i in range(100):
        extra.append(
            _row(
                f"ORD-ENRICH-{order_counter + i:05d}",
                random.randint(100_000, 500_000),
                random.randint(5_000, 20_000),
                "Received",
                "Delivered",
            )
        )
    order_counter += 100

    # 2b. Received + jarak jauh + nilai MENENGAH (500-750k) -> AMAN
    #     Zona abu-abu: di bawah ambang fraud 750k, harus aman.
    for i in range(120):
        extra.append(
            _row(
                f"ORD-ENRICH-{order_counter + i:05d}",
                random.randint(500_000, 750_000),
                random.randint(5_000, 20_000),
                "Received",
                "Delivered",
            )
        )
    order_counter += 120

    # 3. Rejected/Unreachable + jarak jauh -> fraud
    for i in range(80):
        extra.append(
            _row(
                f"ORD-ENRICH-{order_counter + i:05d}",
                random.randint(200_000, 1_200_000),
                random.randint(2_000, 10_000),
                "Rejected/Unreachable",
                "Failed",
            )
        )
    order_counter += 80

    # 4. Not Received (jarak berapa pun) -> fraud
    for i in range(30):
        extra.append(
            _row(
                f"ORD-ENRICH-{order_counter + i:05d}",
                random.randint(100_000, 1_500_000),
                random.randint(10, 15_000),
                "Not Received",
                "Delivered",
            )
        )
    order_counter += 30

    # 5. Received + jarak normal + nilai tinggi -> AMAN
    for i in range(40):
        extra.append(
            _row(
                f"ORD-ENRICH-{order_counter + i:05d}",
                random.randint(800_000, 1_500_000),
                random.randint(100, 2_000),
                "Received",
                "Delivered",
            )
        )

    all_rows = rows + extra
    for r in all_rows:
        r["fraud"] = str(is_fraud(r))

    fieldnames = list(all_rows[0].keys())
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    n_fraud = sum(1 for r in all_rows if r["fraud"] == "1")
    print(f"OK: {len(all_rows)} baris ({len(extra)} baru). Fraud: {n_fraud} ({n_fraud/len(all_rows):.1%})")
    print("Output:", OUT_PATH)


if __name__ == "__main__":
    main()
