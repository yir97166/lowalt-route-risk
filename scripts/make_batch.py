"""Day 10：5 组批量 OD 的 λ=0 / λ=1 汇总（走廊外可飞 OD）。

只统计 role 为 ``core`` 或 ``batch`` 的 OD；``infeasible_example``（端点落在
硬禁飞走廊内）不参与批量统计，单独在 baseline/compare 里记为不可达反例。

输出：
    results/od_summary.csv      5 组 OD 的距离 / C / 变化 / 穿越 / 吸附偏移
    figures/10_batch_od.png     5 组 OD 的 λ=0→λ=1 移动方向
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_MPL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
if not os.environ.get("MPLCONFIGDIR"):
    os.environ["MPLCONFIGDIR"] = str(_MPL_CACHE)

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MAX_SNAP_M = 300.0

from src.config import load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.mask import blocked_mask, feasible_od, restricted_mask, validate_path  # noqa: E402
from src.router import plan_route_weighted, route_exposure_m  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OFF = {"luohu_to_futian": (8, -16), "futian_to_luohu": (8, 8)}

SHORT = {
    "luohu_to_futian": "罗湖—福田",
    "futian_to_luohu": "福田—罗湖",
    "north_station_to_futian": "北站—福田",
    "longhua_to_futian": "龙华—福田",
    "buji_to_luohu": "布吉—罗湖",
}


def main() -> int:
    cfg = load_config()
    grid = build_grid(cfg)
    blocked = blocked_mask(cfg, grid)
    restricted = restricted_mask(cfg, grid)
    graph = build_graph(grid, blocked, cfg.grid.connectivity)
    pop, exposure = load_grid_arrays(cfg, grid)

    rows: list[dict] = []
    for od in cfg.od_pairs:
        if od.role == "infeasible_example":
            continue
        s, d, feasible = feasible_od(cfg, grid, blocked, od, MAX_SNAP_M)
        if not feasible:
            rows.append({"od": od.name, "role": od.role, "reachable": False,
                         "start_offset_m": round(s.offset_m, 1),
                         "dest_offset_m": round(d.offset_m, 1),
                         "note": "endpoint_in_hard_zone"})
            continue
        start, goal = (s.row, s.col), (d.row, d.col)
        base = plan_route_weighted(graph, grid, start, goal, exposure, lam=0.0)
        wtd = plan_route_weighted(graph, grid, start, goal, exposure, lam=1.0)
        check = validate_path(list(wtd.cells), grid, cfg, blocked=blocked)
        c0 = route_exposure_m(graph, base.cells, exposure)
        c1 = route_exposure_m(graph, wtd.cells, exposure)
        n_zone = int(sum(bool(restricted[r, c]) for r, c in wtd.cells))
        change = (c1 / c0 - 1.0) * 100.0 if c0 > 0 else 0.0
        rows.append({
            "od": od.name, "role": od.role, "reachable": True,
            "snap_origin_m": round(s.offset_m, 1),
            "snap_dest_m": round(d.offset_m, 1),
            "base_length_km": round(base.length_m / 1000.0, 3),
            "length_km": round(wtd.length_m / 1000.0, 3),
            "straight_km": round(wtd.straight_m / 1000.0, 3),
            "detour_ratio": round(wtd.detour_ratio, 4),
            "C_lambda0": round(c0 / 1000.0, 3),
            "C_lambda1": round(c1 / 1000.0, 3),
            "C_change_pct": round(change, 2),
            "length_change_pct": round((wtd.length_m / base.length_m - 1.0) * 100.0, 2),
            "hard_crossings": check.crossings,
            "restricted_cells": n_zone,
            "valid": check.ok,
        })

    df = pd.DataFrame(rows)
    out_csv = cfg.resolve("results/od_summary.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(df.to_string(index=False))
    print(f"表：{out_csv}")

    reach = df[df["reachable"].fillna(False)]
    fig, ax = plt.subplots(figsize=(9.2, 5.8), dpi=170)
    for _, r in reach.iterrows():
        label = SHORT.get(r["od"], r["od"])
        ax.scatter(r["base_length_km"], r["C_lambda0"], marker="o", s=46, color="#1f77b4", zorder=3)
        ax.scatter(r["length_km"], r["C_lambda1"], marker="^", s=46, color="#d62728", zorder=3)
        ax.annotate("", xy=(r["length_km"], r["C_lambda1"]),
                    xytext=(r["base_length_km"], r["C_lambda0"]),
                    arrowprops=dict(arrowstyle="->", color="gray", lw=1.1, alpha=0.8))
        offs = OFF.get(r["od"], (7, 6))
        ax.annotate(label, (r["base_length_km"], r["C_lambda0"]),
                    textcoords="offset points", xytext=offs, fontsize=9)
    ax.scatter([], [], marker="o", color="#1f77b4", label="λ=0（最短）")
    ax.scatter([], [], marker="^", color="#d62728", label="λ=1（低暴露）")
    ax.set_xlabel("路线长度（km）")
    ax.set_ylabel("累计暴露 C（代理·米 ×1000）")
    ax.set_title("5 组可飞 OD：λ=0→λ=1 的长度—暴露移动（200 m 网格，60 m 单层）", fontsize=11)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", fontsize=9)
    out_fig = cfg.resolve("figures/10_batch_od.png")
    fig.tight_layout()
    fig.savefig(out_fig)
    plt.close(fig)
    print(f"图：{out_fig}")
    return 0 if bool(reach["valid"].all()) and bool((reach["hard_crossings"] == 0).all()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
