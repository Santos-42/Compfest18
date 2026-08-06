"""Single source of truth for synthetic fraud labels."""


def is_fraud(row: dict) -> int:
    report = (row.get("customer_report") or "").strip()
    status = (row.get("system_status") or "").strip()
    try:
        gps_distance = float(row.get("gps_distance_meters") or 0)
    except (TypeError, ValueError):
        gps_distance = 0.0
    try:
        item_value = float(row.get("item_value") or 0)
    except (TypeError, ValueError):
        item_value = 0.0

    if report == "Not Received":
        return 1
    if report == "Rejected/Unreachable" and gps_distance > 1_500:
        return 1
    if report == "Received" and gps_distance > 5_000 and item_value > 750_000:
        return 1
    if status == "Delivered" and report == "Not Received":
        return 1
    return 0
