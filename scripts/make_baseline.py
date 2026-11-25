"""Day 3 入口：核心 OD 的最短可行路线 baseline（λ = 0）。

输出：
    results/baseline.csv       指标一行
    results/baseline_path.csv  路线格心序列
    figures/02_shortest_path.png
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_MPL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
if not os.environ.get("MPLCONFIGDIR"):
    os.environ["MPLCONFIGDIR"] = str(_MPL_CACHE)

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 吸附超过该距离，说明端点本身落在硬禁飞区里，应判不可达，而不是把端点挪走。
MAX_SNAP_M = 300.0

from src.config import load_config  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.graph import build_graph, graph_stats  # noqa: E402
from src.mask import (  # noqa: E402
    blocked_mask,
    feasible_od, od_feasibility,
    nearest_free_cell,
    path_to_lonlat,
    restricted_mask,
    validate_path,
)
from src.router import plan_route  # noqa: E402
from src.viz import plot_route  # noqa: E402


def load_population(cfg, grid) -> np.ndarray:
    """从 Day 1 的网格人口表恢复 (rows, cols) 数组。"""
    csv_path = cfg.resolve("data/processed/grid_population.csv")
    if not csv_path.exists():
        raise FileNotFoundError(
            f"缺少 {csv_path}；先跑 scripts/make_population_map.py"
        )
    df = pd.read_csv(csv_path)
    pop = np.zeros(grid.shape, dtype=float)
    pop[df["row"].to_numpy(), df["col"].to_numpy()] = df["population"].to_numpy()
    return pop


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 3：核心 OD 最短路 baseline")
    ap.add_argument("--config", default=None)
    ap.add_argument("--out-csv", default="results/baseline.csv")
    ap.add_argument("--out-path", default="results/baseline_path.csv")
    ap.add_argument("--out-fig", default="figures/02_shortest_path.png")
    args = ap.parse_args()

    cfg = load_config(args.config)
    grid = build_grid(cfg)
    blocked = blocked_mask(cfg, grid)
    restricted = restricted_mask(cfg, grid)
    graph = build_graph(grid, blocked, cfg.grid.connectivity)
    stats = graph_stats(graph)
    print(f"图：{stats['nodes']:,} 节点 / {stats['edges']:,} 边 / "
          f"{stats['components']} 个连通分量（最大 {stats['largest_component']:,}）")

    od = cfg.od_pairs[0]
    rows: list[dict] = []
    core_route = None
    for od in cfg.od_pairs:
        s, d, feasible, reason = od_feasibility(cfg, grid, blocked, od, MAX_SNAP_M)
        if not feasible:
            print(f"{od.name}: 端点落在硬禁飞区内（吸附 {s.offset_m:.0f}/{d.offset_m:.0f} m），判不可达")
            rows.append({"od": od.name, "lambda": 0.0, "reachable": False,
                         "start_offset_m": round(s.offset_m, 1),
                         "dest_offset_m": round(d.offset_m, 1),
                         "note": reason})
            continue
        try:
            route = plan_route(graph, grid, (s.row, s.col), (d.row, d.col))
        except Exception as exc:  # noqa: BLE001 - 批量实验里记录不可达即可
            print(f"{od.name}: 不可达（{type(exc).__name__}: {exc}）")
            rows.append({"od": od.name, "lambda": 0.0, "reachable": False,
                         "start_offset_m": round(s.offset_m, 1),
                         "dest_offset_m": round(d.offset_m, 1)})
            continue
        check = validate_path(list(route.cells), grid, cfg, blocked=blocked)
        n_in_zone = int(sum(bool(restricted[r, c]) for r, c in route.cells))
        print(f"{od.name}: {len(route.cells)} 格，{route.length_m / 1000:.3f} km，"
              f"绕行率 {route.detour_ratio:.3f}，穿越 {check.crossings}，ok={check.ok}"
              f"（吸附 {s.offset_m:.1f}/{d.offset_m:.1f} m，净空区内 {n_in_zone} 格）")
        if not check.ok:
            print("  问题：" + "；".join(check.issues))
        rows.append({
            "od": od.name,
            "lambda": 0.0,
            "reachable": True,
            "graph_nodes": stats["nodes"],
            "graph_edges": stats["edges"],
            "graph_components": stats["components"],
            "start_row": s.row,
            "start_col": s.col,
            "start_offset_m": round(s.offset_m, 1),
            "dest_row": d.row,
            "dest_col": d.col,
            "dest_offset_m": round(d.offset_m, 1),
            "n_cells": len(route.cells),
            "length_m": round(route.length_m, 1),
            "straight_m": round(route.straight_m, 1),
            "detour_ratio": round(route.detour_ratio, 4),
            "hard_crossings": check.crossings,
            "min_clearance_m": round(check.min_clearance_m, 1),
            "restricted_cells": n_in_zone,
            "restricted_share": round(n_in_zone / len(route.cells), 4),
            "valid": check.ok,
        })
        if core_route is None:
            core_route = route

    out_csv = cfg.resolve(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    reach = df[df["reachable"].fillna(False)]
    n_infeasible = int((~df["reachable"].fillna(False)).sum())
    n_bad = int((reach["hard_crossings"] != 0).sum()) if len(reach) else 0
    if "valid" in reach:
        n_bad = max(n_bad, int((~reach["valid"].fillna(False)).sum()))

    assert core_route is not None
    lonlat = path_to_lonlat(list(core_route.cells), grid, cfg.crs_input)
    path_df = pd.DataFrame({
        "seq": np.arange(len(core_route.cells)),
        "row": [r for r, _ in core_route.cells],
        "col": [c for _, c in core_route.cells],
        "lon": lonlat[:, 0].round(6),
        "lat": lonlat[:, 1].round(6),
    })
    out_path = cfg.resolve(args.out_path)
    path_df.to_csv(out_path, index=False, encoding="utf-8")

    pop = load_population(cfg, grid)
    fig_path = plot_route(cfg, grid, pop, list(core_route.cells), cfg.resolve(args.out_fig))
    print(f"指标：{out_csv}（{len(df)} 组 OD：可达 {len(reach)}，不可达 {n_infeasible}，"
          f"穿越/无效 {n_bad}）")
    print(f"路线：{out_path}（{len(path_df)} 点，核心 OD）")
    print(f"图：{fig_path}")
    return 0 if (n_bad == 0 and core_route is not None) else 1


if __name__ == "__main__":
    raise SystemExit(main())
