"""p95 归一化分位数的敏感性：不同分位数下的核心 OD 权衡。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.config import load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.mask import blocked_mask, feasible_od  # noqa: E402
from src.risk import normalize_population, risk_surface  # noqa: E402
from src.router import plan_route, plan_route_weighted, route_exposure_m  # noqa: E402
from src.grid import build_grid  # noqa: E402

cfg = load_config()
grid = build_grid(cfg)
pop, _ = load_grid_arrays(cfg, grid)
blocked = blocked_mask(cfg, grid)
graph = build_graph(grid, blocked)
od = cfg.od_pairs[0]
s, g, ok = feasible_od(cfg, grid, blocked, od)
if not ok:
    raise SystemExit("核心 OD 不可达")
start, goal = (s.row, s.col), (g.row, g.col)
base = plan_route(graph, grid, start, goal)
rows = []
for pct in (90.0, 95.0, 99.0):
    pop_norm, pval = normalize_population(pop, pct)
    exposure = risk_surface(pop_norm, cfg.risk)
    c0 = route_exposure_m(graph, base.cells, exposure)
    first = None
    n_sol = 0
    prev = None
    c1 = None
    len1 = base.length_m
    for k in range(81):
        lam = round(k * 0.025, 3)
        r = plan_route_weighted(graph, grid, start, goal, exposure, lam)
        if prev is None or r.cells != prev:
            n_sol += 1
            prev = r.cells
        if lam == 1.0:
            c1 = route_exposure_m(graph, r.cells, exposure)
            len1 = r.length_m
        if first is None and r.length_m > base.length_m + 1e-6:
            first = lam
    rows.append({
        "percentile": pct, "p_value": round(pval, 3),
        "c_l0": round(c0, 1), "c_l1": round(c1, 1) if c1 else None,
        "len1_km": round(len1 / 1000.0, 3),
        "first_detour_lambda": first, "n_solutions": n_sol,
    })
out = pd.DataFrame(rows)
out.to_csv(cfg.resolve("results/p95_sensitivity.csv"), index=False, encoding="utf-8")
print(out.to_string(index=False))
