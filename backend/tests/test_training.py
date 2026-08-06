from fraud_label_rules import is_fraud


def test_shared_fraud_rules_cover_expected_patterns():
    assert is_fraud({"customer_report": "Not Received"}) == 1
    assert is_fraud({"customer_report": "Rejected/Unreachable", "gps_distance_meters": 1501}) == 1
    assert is_fraud({"customer_report": "Received", "gps_distance_meters": 5001, "item_value": 750001}) == 1
    assert is_fraud({"customer_report": "Received", "gps_distance_meters": 5001, "item_value": 750000}) == 0
