import logging

logger = logging.getLogger(__name__)

try:
    from ortools.sat.python import cp_model

    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logger.warning("ortools tidak tersedia; menggunakan greedy route")


def optimize_route(
    distances: list[list[float]],
    durations: list[list[float]] | None = None,
    mode: str = "distance",
) -> list[int]:
    costs = durations if mode == "time" and durations is not None else distances
    _validate_matrix(costs)
    node_count = len(costs)
    if node_count == 0:
        return []
    if node_count == 1:
        return [0]
    if node_count == 2:
        return [0, 1, 0]

    if ORTOOLS_AVAILABLE:
        try:
            return _cp_sat_route(costs)
        except Exception as exc:
            logger.warning("CP-SAT gagal: %s; menggunakan greedy", exc)
    return _greedy_route(costs)


def _validate_matrix(matrix):
    if not matrix or any(len(row) != len(matrix) for row in matrix):
        raise ValueError("Matrix routing harus persegi dan tidak kosong.")
    if any(value < 0 for row in matrix for value in row):
        raise ValueError("Biaya routing tidak boleh negatif.")


def _cp_sat_route(costs: list[list[float]]) -> list[int]:
    node_count = len(costs)
    model = cp_model.CpModel()
    arcs = []
    for source in range(node_count):
        for target in range(node_count):
            if source != target:
                arcs.append((source, target, model.NewBoolVar(f"arc_{source}_{target}")))
    model.AddCircuit(arcs)
    model.Minimize(
        sum(arc * int(round(costs[source][target])) for source, target, arc in arcs)
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("CP-SAT tidak menemukan solusi")

    next_of = {
        source: target
        for source, target, arc in arcs
        if solver.Value(arc)
    }
    route = [0]
    current = 0
    while len(route) < node_count:
        current = next_of[current]
        route.append(current)
    route.append(0)
    return route


def _greedy_route(costs: list[list[float]]) -> list[int]:
    visited = {0}
    route = [0]
    current = 0
    while len(visited) < len(costs):
        candidates = [
            (costs[current][target], target)
            for target in range(1, len(costs))
            if target not in visited
        ]
        _, target = min(candidates, key=lambda item: (item[0], item[1]))
        route.append(target)
        visited.add(target)
        current = target
    route.append(0)
    return route


def route_totals(route: list[int], matrix: list[list[float]]) -> float:
    return sum(matrix[source][target] for source, target in zip(route, route[1:]))
