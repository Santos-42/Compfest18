from services import eta_service, routing_service


def test_route_is_closed_for_greedy_fallback(monkeypatch):
    monkeypatch.setattr(routing_service, "ORTOOLS_AVAILABLE", False)
    matrix = [
        [0, 10, 30],
        [10, 0, 15],
        [30, 15, 0],
    ]
    assert routing_service.optimize_route(matrix) == [0, 1, 2, 0]


def test_weather_factor_changes_eta_and_return_leg(monkeypatch):
    monkeypatch.setattr(eta_service.settings, "TRAFFIC_FACTOR", {"normal": 1.0})
    monkeypatch.setattr(eta_service.settings, "WEATHER_FACTOR", {"Cerah": 1.0, "Hujan Lebat": 2.0})
    route = [0, 1, 0]
    points = [{"lat": 0, "lng": 0}, {"lat": 0, "lng": 0.1}]
    distances = [[0, 1000], [1000, 0]]
    durations = [[0, 600], [600, 0]]
    clear = eta_service.build_eta_timestamps(
        route, points, distances, durations, "normal", [{"weather": "Cerah", "temperature": 30}]
    )
    rain = eta_service.build_eta_timestamps(
        route, points, distances, durations, "normal", [{"weather": "Hujan Lebat", "temperature": 25}]
    )
    assert rain["eta_list"][0]["duration_s"] > clear["eta_list"][0]["duration_s"]
    assert rain["return_leg"]["duration_s"] > clear["return_leg"]["duration_s"]
    assert rain["return_leg"]["cumulative_distance_m"] == 2000
