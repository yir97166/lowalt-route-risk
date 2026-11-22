"""参数敏感性：遮蔽系数 s 如何影响 λ—路线切换阈值。

目的：遮蔽系数 0.30 是工程假设（SORA 把遮蔽当作缓解措施 M1，而不是固定系数）。
因为 exposure = pop_norm × severity × (1 − s) × alt_factor，s 只是一个常数乘子，
理论预测：路线切换阈值 λ*_s 与 (1 − s) 成反比，即 λ*_s = λ*_0.3 × (1 − 0.3) / (1 − s)。

本脚本对 s = 0.2 / 0.3 / 0.4 各跑一遍 λ 扫描，验证：
1) 三组解的路线集合相同；2) 切换阈值按上式平移；3) 因此结论对 s 的绝对值不敏感，
   报告里只需说明 s 取值，不必声称 0.30 有依据。

用法：
    .venv\\Scripts\\python.exe scripts\\make_param_sensitivity.py
输出：
    results/param_sensitivity.csv
    results/param_sensitivity_summary.csv
    figures/07_param_sensitivity.png
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

_MPL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
if not os.environ.get("MPLCONFIGDIR"):
    os.environ["MPLCONFIGDIR"] = str(_MPL_CACHE)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.data import load_grid_arrays
from src.grid import build_grid
from src.graph import build_graph
from src.mask import blocked_mask, point_to_metric, nearest_free_cell
from src.router import plan_route_weighted, route_exposure_m

SHELTERS = (0.2, 0.3, 0.4)
LAMBDAS = np.round(np.arange(0.0, 2.0001, 0.025), 4)
CORE_OD = "luohu_to_futian"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    grid = build_grid(cfg)
    pop, _ = load_grid_arrays(cfg, grid)
    blocked = blocked_mask(cfg, grid)
    graph = build_graph(grid, blocked, connectivity=cfg.grid.connectivity)

    od = next(o for o in cfg.od_pairs if o.name == CORE_OD)
    ox, oy = point_to_metric(cfg, od.origin[0], od.origin[1])
    dx, dy = point_to_metric(cfg, od.destination[0], od.destination[1])
    start = nearest_free_cell(cfg, grid, blocked, od.origin[0], od.origin[1])
    goal = nearest_free_cell(cfg, grid, blocked, od.destination[0], od.destination[1])

    # 与 src/risk.py 同一口径：非零格 p95 归一化，severity=1.0，60 m 层 alt_factor=1.0
    nonzero = pop[pop > 0]
    p95 = float(np.percentile(nonzero, cfg.risk.population_percentile))
    pop_norm = np.clip(pop / p95, 0.0, 1.0)

    out_dir = cfg.root / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    summary: list[dict] = []

    s_node = (start.row, start.col)
    g_node = (goal.row, goal.col)
    base_len = None
    for s in SHELTERS:
        exposure = pop_norm * cfg.risk.severity * (1.0 - s) * 1.0
        prev = None
        threshold = None
        seen: list[tuple[float, float]] = []
        for lam in LAMBDAS:
            route = plan_route_weighted(graph, grid, s_node, g_node, exposure, float(lam))
            length = route.length_m
            exp_m = route_exposure_m(graph, route.cells, exposure)
            if base_len is None:
                base_len = length
            switched = length > base_len + 1.0
            if switched and threshold is None:
                threshold = float(lam)
            key = (round(length, 3), round(exp_m, 3))
            if key not in seen:
                seen.append(key)
            rows.append(
                {
                    "shelter": s,
                    "lambda": float(lam),
                    "length_km": round(length / 1000.0, 4),
                    "exposure_m": round(exp_m, 3),
                    "exposure_norm_m": round(exp_m / (1.0 - s), 3),
                    "switched": switched,
                }
            )
            prev = length
        summary.append(
            {
                "shelter": s,
                "lambda_threshold": threshold,
                "predicted_threshold": None,
                "distinct_solutions": len(seen),
            }
        )

    base_thr = next(r["lambda_threshold"] for r in summary if r["shelter"] == 0.3)
    for r in summary:
        r["predicted_threshold"] = round(
            base_thr * (1.0 - 0.3) / (1.0 - r["shelter"]), 3
        )

    with (out_dir / "param_sensitivity.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with (out_dir / "param_sensitivity_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    print("shelter  lambda*  predicted  solutions")
    for r in summary:
        print(
            f"{r['shelter']:.1f}      {r['lambda_threshold']}   "
            f"{r['predicted_threshold']}     {r['distinct_solutions']}"
        )

    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=150)
    for s in SHELTERS:
        sub = [r for r in rows if r["shelter"] == s]
        ax.plot(
            [r["lambda"] for r in sub],
            [r["length_km"] for r in sub],
            lw=1.8,
            label=f"遮蔽系数 = {s}",
        )
    ax.set_xlabel("风险权重 λ")
    ax.set_ylabel("核心 OD 路线长度 (km)")
    ax.set_title("遮蔽系数对 λ—路线切换阈值的影响（核心 OD，60 m）")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(cfg.root / "figures" / "07_param_sensitivity.png")
    print("written: results/param_sensitivity*.csv, figures/07_param_sensitivity.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
