"""Day 4 入口：人口暴露加权路线 vs baseline（λ = 1）。

边权改为 ``length_m × (1 + λ × exposure)``；对 5 组 OD 各跑两条线，
比较距离增量与累计暴露变化，核心 OD 出对比图。

输出：
    results/compare.csv          5 组 OD 的 baseline vs 加权指标
    results/weighted_path.csv    核心 OD 的加权路线格心序列
    figures/03_route_compare.png 核心 OD 两条路线对比图
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

# 与 make_baseline 一致：吸附超过 300 m 视为端点落在硬禁飞区内，判不可达。
MAX_SNAP_M = 300.0

from src.config import load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph, graph_stats  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.mask import (  # noqa: E402
    blocked_mask,
    feasible_od, od_feasibility,
    nearest_free_cell,
    path_to_lonlat,
    restricted_mask,
    validate_path,
)
from src.router import plan_route_weighted, route_exposure_m  # noqa: E402
from src.viz import plot_route_compare  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 4：暴露加权路线 vs baseline")
    ap.add_argument("--config", default=None)
    ap.add_argument("--lambda", dest="lam", type=float, default=1.0)
    ap.add_argument("--out-csv", default="results/compare.csv")
    ap.add_argument("--out-path", default="results/weighted_path.csv")
    ap.add_argument("--out-fig", default="figures/03_route_compare.png")
    args = ap.parse_args()

    cfg = load_config(args.config)
    grid = build_grid(cfg)
    blocked = blocked_mask(cfg, grid)
    restricted = restricted_mask(cfg, grid)
    graph = build_graph(grid, blocked, cfg.grid.connectivity)
    stats = graph_stats(graph)
    print(f"图：{stats['nodes']:,} 节点 / {stats['edges']:,} 边 / "
          f"{stats['components']} 个连通分量（最大 {stats['largest_component']:,}）")

    pop, exposure = load_grid_arrays(cfg, grid)
    print(f"暴露代理：max={exposure.max():.3f}，均值(非零)={exposure[exposure > 0].mean():.3f}")

    rows: list[dict] = []
    core = None
    for od in cfg.od_pairs:
        s, d, feasible, reason = od_feasibility(cfg, grid, blocked, od, MAX_SNAP_M)
        if not feasible:
            print(f"{od.name}: 端点落在硬禁飞区内（吸附 {s.offset_m:.0f}/{d.offset_m:.0f} m），判不可达")
            rows.append({"od": od.name, "lambda": args.lam, "reachable": False,
                         "start_offset_m": round(s.offset_m, 1),
                         "dest_offset_m": round(d.offset_m, 1),
                         "note": reason})
            continue
        start, goal = (s.row, s.col), (d.row, d.col)
        try:
            base = plan_route_weighted(graph, grid, start, goal, exposure, lam=0.0)
            wtd = plan_route_weighted(graph, grid, start, goal, exposure, lam=args.lam)
        except Exception as exc:  # noqa: BLE001 - 批量实验里记录不可达即可
            print(f"{od.name}: 不可达（{type(exc).__name__}: {exc}）")
            rows.append({"od": od.name, "lambda": args.lam, "reachable": False})
            continue

        check = validate_path(list(wtd.cells), grid, cfg, blocked=blocked)
        n_zone = int(sum(bool(restricted[r, c]) for r, c in wtd.cells))
        exp_base_m = route_exposure_m(graph, base.cells, exposure)
        exp_wtd_m = route_exposure_m(graph, wtd.cells, exposure)
        delta_km = (wtd.length_m - base.length_m) / 1000.0
        delta_pct = (wtd.length_m / base.length_m - 1.0) * 100.0
        exp_drop = (1.0 - exp_wtd_m / exp_base_m) * 100.0 if exp_base_m > 0 else 0.0

        print(f"{od.name}: baseline {base.length_m / 1000:.3f} km / "
              f"加权 {wtd.length_m / 1000:.3f} km（{delta_pct:+.2f}%）· "
              f"暴露 {exp_base_m / 1000:.3f} → {exp_wtd_m / 1000:.3f}（下降 {exp_drop:.1f}%）· "
              f"穿越 {check.crossings}，ok={check.ok}")
        rows.append({
            "od": od.name,
            "lambda": args.lam,
            "reachable": True,
            "base_length_m": round(base.length_m, 1),
            "weighted_length_m": round(wtd.length_m, 1),
            "delta_m": round(wtd.length_m - base.length_m, 1),
            "delta_pct": round(delta_pct, 3),
            "base_detour_ratio": round(base.detour_ratio, 4),
            "weighted_detour_ratio": round(wtd.detour_ratio, 4),
            "base_exposure_m": round(exp_base_m, 1),
            "weighted_exposure_m": round(exp_wtd_m, 1),
            "exposure_drop_pct": round(exp_drop, 2),
            "base_mean_exposure": round(exp_base_m / base.length_m, 6),
            "weighted_mean_exposure": round(exp_wtd_m / wtd.length_m, 6),
            "hard_crossings": check.crossings,
            "restricted_cells": n_zone,
            "restricted_share": round(n_zone / len(wtd.cells), 4),
            "valid": check.ok,
            "same_as_baseline": tuple(wtd.cells) == tuple(base.cells),
        })
        if core is None:
            core = (base, wtd)

    df = pd.DataFrame(rows)
    out_csv = cfg.resolve(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")

    assert core is not None
    base, wtd = core
    lonlat = path_to_lonlat(list(wtd.cells), grid, cfg.crs_input)
    pd.DataFrame({
        "seq": np.arange(len(wtd.cells)),
        "row": [r for r, _ in wtd.cells],
        "col": [c for _, c in wtd.cells],
        "lon": lonlat[:, 0].round(6),
        "lat": lonlat[:, 1].round(6),
    }).to_csv(cfg.resolve(args.out_path), index=False, encoding="utf-8")

    fig = plot_route_compare(
        cfg, grid, pop, list(base.cells), list(wtd.cells),
        cfg.resolve(args.out_fig), lam=args.lam,
        od_label=f"核心 OD：{cfg.od_pairs[0].name}",
    )
    reach = df[df["reachable"].fillna(False)]
    n_infeasible = int((~df["reachable"].fillna(False)).sum())
    n_bad = int((reach["hard_crossings"] != 0).sum()) if "hard_crossings" in reach else 0
    if "valid" in reach:
        n_bad = max(n_bad, int((~reach["valid"].fillna(False)).sum()))
    print(f"指标：{out_csv}（{len(df)} 组 OD：可达 {len(reach)}，不可达 {n_infeasible}，"
          f"穿越/无效 {n_bad}）")
    print(f"图：{fig}")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
