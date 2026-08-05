"""Routing Service — OR-Tools CP-SAT (TSP) untuk optimasi urutan pengiriman.

Node 0 = origin (gudang). Cari urutan kunjungan yang meminimalkan total jarak.
Fallback: nearest-neighbor greedy jika ortools tidak tersedia.
"""
import logging

logger = logging.getLogger(__name__)

try:
    from ortools.sat.python import cp_model

    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logger.warning("ortools tidak terpasang — pakai greedy nearest-neighbor.")


def optimize_route(distances: list[list[float]]) -> list[int]:
    """Return urutan indeks titik (0 = origin, lalu stop 1..n) yang optimal.

    Jarak satuan bebas (meter/detik) — yang penting relatifnya.
    """
    n = len(distances)
    if n <= 2:
        return list(range(n))

    if ORTOOLS_AVAILABLE:
        try:
            return _cp_sat_route(distances)
        except Exception as exc:
            logger.warning("CP-SAT gagal (%s), fallback greedy.", exc)

    return _greedy_route(distances)


def _cp_sat_route(distances: list[list[float]]) -> list[int]:
    """TSP via circuit constraint. n kecil (<20), selesai cepat."""
    n = len(distances)
    model = cp_model.CpModel()

    int_max = max(
        int(max((d for row in distances for d in row), default=0)) * n + 1000, 1000
    )
    next_var = [model.NewIntVar(0, n - 1, f"next_{i}") for i in range(n)]
    arcs = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            arcs.append((i, j, model.NewBoolVar(f"arc_{i}_{j}")))
    model.AddCircuit(arcs)

    # jumlahkan jarak edge yang terpilih: biaya arc * jarak
    edge_cost = []
    for i, j, arc in arcs:
        cost = int(round(distances[i][j]))
        edge_cost.append(arc * cost)
    model.Minimize(sum(edge_cost))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("CP-SAT tidak menemukan solusi")

    # Rekonstruksi siklus dari node 0
    next_of = {}
    for i, j, arc in arcs:
        if solver.Value(arc):
            next_of[i] = j
    route = [0]
    current = 0
    while len(route) < n:
        current = next_of[current]
        route.append(current)
    return route


def _greedy_route(distances: list[list[float]]) -> list[int]:
    n = len(distances)
    visited = {0}
    route = [0]
    current = 0
    while len(route) < n:
        candidates = [
            (distances[current][j], j)
            for j in range(n)
            if j not in visited and distances[current][j] > 0
        ]
        if not candidates:
            # sisanya tidak terjangkau — tambahkan berurutan
            for j in range(n):
                if j not in visited:
                    route.append(j)
                    visited.add(j)
            return route
        _, nxt = min(candidates)
        route.append(nxt)
        visited.add(nxt)
        current = nxt
    return route
