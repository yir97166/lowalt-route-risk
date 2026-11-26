"""按 SORA 2.5 Table 2 的 iGRC 分档做路线对照（只作参照，不做审定）。

参考机型：最大特征尺寸 ≤3 m、最大巡航速度 ≤35 m/s（Table 2 第 2 列）。
人口密度按 200 m 格换算：density = pop_cell × 25（人/km²）。
iGRC 取航线经过格子的**最大**密度档（SORA 2.3.1(h)）。

输出：
- results/igrc_band.csv：各候选路线的最大密度、iGRC、各档格数占比
- results/igrc_threshold.csv：按密度阈值硬避让时的可行性/长度
- results/igrc_weight.csv：按档位加权（length × (1 + κ × band)）的路线扫描
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
from src.router import path_length, plan_route, plan_route_weighted, route_exposure_m  # noqa: E402

BANDS = [(25, 4), (250, 5), (2500, 6), (25000, 7), (250000, 8), (float("inf"), 9)]


def igrc(density: float) -> int:
    for hi, cls in BANDS:
        if density < hi:
            return cls
    return 9


def band_index(density: float) -> int:
    """0=<25, 1=<250, ..., 5=>=250000，用于加权。"""
    for i, (hi, _) in enumerate(BANDS):
        if density < hi:
            return i
    return len(BANDS) - 1


def main() -> int:
    cfg = load_config()
    grid = build_grid(cfg)
    pop, exposure = load_grid_arrays(cfg, grid)
    density = pop * 25.0
    blocked = blocked_mask(cfg, grid)
    graph = build_graph(grid, blocked)
    core = next(od for od in cfg.od_pairs if od.role == "core")
    origin, dest, _ = feasible_od(cfg, grid, blocked, core)
    s, g = (origin.row, origin.col), (dest.row, dest.col)

    routes = {
        "A 最短": plan_route(graph, grid, s, g).cells,
        "D C 加权 λ=1": plan_route_weighted(graph, grid, s, g, exposure, 1.0).cells,
    }

    rows = []
    for name, cells in routes.items():
        dens = np.array([density[c] for c in cells])
        rows.append({
            "route": name,
            "length_km": path_length(graph, cells) / 1000.0,
            "max_density": dens.max(),
            "iGRC": igrc(dens.max()),
            "p95_band_share": float((dens >= 25000).mean()),
            "p99_band_share": float((dens >= 250000).mean()),
            "origin_density": density[s],
            "dest_density": density[g],
        })
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "igrc_band.csv", index=False, encoding="utf-8")

    # 阈值硬避让：找最低可行密度档，再求该阈值下的最短路
    thr_rows = []
    for thr in (250, 2500, 25000, 250000):
        blocked_t = blocked | (density > thr)
        if density[s] > thr or density[g] > thr:
            thr_rows.append({"threshold": thr, "feasible": False, "length_km": np.nan, "reason": "端点密度超过阈值"})
            continue
        try:
            ss = nearest_free_cell(cfg, grid, blocked_t, origin.lon, origin.lat)
            gg = nearest_free_cell(cfg, grid, blocked_t, dest.lon, dest.lat)
            gt = build_graph(grid, blocked_t)
            cells = plan_route(gt, grid, (ss.row, ss.col), (gg.row, gg.col)).cells
        except Exception as exc:  # noqa: BLE001
            thr_rows.append({"threshold": thr, "feasible": False, "length_km": np.nan, "reason": type(exc).__name__})
            continue
        dens = np.array([density[c] for c in cells])
        thr_rows.append({
            "threshold": thr,
            "feasible": True,
            "length_km": path_length(gt, cells) / 1000.0,
            "max_density": dens.max(),
            "iGRC": igrc(dens.max()),
            "reason": "",
        })
    pd.DataFrame(thr_rows).to_csv(ROOT / "results" / "igrc_threshold.csv", index=False, encoding="utf-8")

    # 档位加权扫描
    wt_rows = []
    for kappa in (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0):
        weight = lambda u, v, d: d["length_m"] * (1.0 + kappa * band_index(density[u]))  # noqa: E731
        cells = list(nx.dijkstra_path(graph, s, g, weight=weight))
        dens = np.array([density[c] for c in cells])
        wt_rows.append({
            "kappa": kappa,
            "length_km": path_length(graph, cells) / 1000.0,
            "c_proxy_m": route_exposure_m(graph, cells, exposure),
            "max_density": dens.max(),
            "iGRC": igrc(dens.max()),
        })
    pd.DataFrame(wt_rows).to_csv(ROOT / "results" / "igrc_weight.csv", index=False, encoding="utf-8")

    print(df.round(2).to_string(index=False))
    print("--- threshold ---")
    print(pd.DataFrame(thr_rows).round(3).to_string(index=False))
    print("--- weight ---")
    print(pd.DataFrame(wt_rows).round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
