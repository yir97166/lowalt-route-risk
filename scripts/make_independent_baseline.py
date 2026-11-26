"""独立目标基线：不依赖 p95 归一化的两种路线，与 C 加权路线对比。

A. 最小长度（纯距离基线）
B. 最小绝对人口暴露 P = Σ 边长 × 两端人口均值（人·米），不做归一化
C. 最小长度但硬避让人口最高的 5% 格子（阈值约束，不做加权）
D. 参考：C 加权 λ=1 路线
输出 results/independent_baseline.csv。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.mask import blocked_mask, feasible_od, nearest_free_cell  # noqa: E402
from src.router import (  # noqa: E402
    path_length,
    plan_route,
    plan_route_weighted,
    route_exposure_m,
)


def _metrics(route_cells, graph, grid, pop, exposure):
    length = path_length(graph, route_cells)
    p_people_m = 0.0
    for a, b in zip(route_cells[:-1], route_cells[1:]):
        w = graph[a][b]["length_m"]
        p_people_m += w * (pop[a] + pop[b]) / 2.0
    cells_pop = np.array([pop[c] for c in route_cells])
    return {
        "length_km": length / 1000.0,
        "p_people_m": p_people_m,
        "c_proxy_m": route_exposure_m(graph, route_cells, exposure),
        "e_mean": route_exposure_m(graph, route_cells, exposure) / length,
        "max_pop": float(cells_pop.max()),
        "pop_p95_share": float((cells_pop >= np.quantile(pop[pop > 0], 0.95)).mean()),
    }


def main() -> int:
    cfg = load_config()
    grid = build_grid(cfg)
    pop, exposure = load_grid_arrays(cfg, grid)
    blocked = blocked_mask(cfg, grid)
    graph = build_graph(grid, blocked)
    core = next(od for od in cfg.od_pairs if od.role == "core")
    origin, dest, _ = feasible_od(cfg, grid, blocked, core)
    s, g = (origin.row, origin.col), (dest.row, dest.col)

    rows = []
    base = plan_route(graph, grid, s, g)
    rows.append({"objective": "A 最小长度", **_metrics(base.cells, graph, grid, pop, exposure)})

    # B：绝对人口暴露最小（人·米），不做归一化
    weight_p = lambda u, v, d: d["length_m"] * (pop[u] + pop[v]) / 2.0
    cells_p = list(nx.dijkstra_path(graph, s, g, weight=weight_p))
    rows.append({"objective": "B 最小人口暴露 P", **_metrics(cells_p, graph, grid, pop, exposure)})

    # C：硬避让人口最高的 5% 格子
    q95 = float(np.quantile(pop[pop > 0], 0.95))
    blocked_hi = blocked | (pop >= q95)
    snap_s = nearest_free_cell(cfg, grid, blocked_hi, origin.lon, origin.lat)
    snap_g = nearest_free_cell(cfg, grid, blocked_hi, dest.lon, dest.lat)
    graph_hi = build_graph(grid, blocked_hi)
    s2, g2 = (snap_s.row, snap_s.col), (snap_g.row, snap_g.col)
    cells_hi = plan_route(graph_hi, grid, s2, g2).cells
    rows.append({"objective": "C 避让最高 5% 人口格", **_metrics(cells_hi, graph_hi, grid, pop, exposure)})

    # D：参考 C 加权 λ=1
    wt = plan_route_weighted(graph, grid, s, g, exposure, 1.0)
    rows.append({"objective": "D C 加权 λ=1（参考）", **_metrics(wt.cells, graph, grid, pop, exposure)})

    df = pd.DataFrame(rows)
    base_length = df.loc[0, "length_km"]
    df["detour"] = df["length_km"] / base_length
    out = ROOT / "results" / "independent_baseline.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    print(df.round(4).to_string(index=False))
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
