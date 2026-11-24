"""③ 起点平移（吸附偏移）敏感性实验。

审核意见：400 m 网格下起点吸附偏移 158.6 m（≈0.4 格），报告只标注未做实验，
无法回答「结果是不是吸附位置的产物」。

做法：对核心 OD 的两个端点整体平移 (±0.5, ±0.5) 格共 9 个位置（含 0,0 基准），
在 100 / 200 / 400 m 三种网格上分别重算 λ=0 与 λ=1 两条路线，
记录长度 L、等效暴露长度 C、平均暴露强度 E、沿路人口密度 ρ̄、绕行率、吸附偏移。

输出：
    results/origin_shift.csv      9 个平移位置 × 3 种网格 × 2 个 λ
    results/origin_shift_summary.csv  每种网格的极差汇总
    figures/08_origin_shift.png   3 个面板：Δ 长度 vs Δ 暴露
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

_MPL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
if not os.environ.get("MPLCONFIGDIR"):
    os.environ["MPLCONFIGDIR"] = str(_MPL_CACHE)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402
from src.data import aggregate_population_to_grid, pick_population_path  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.grid import build_grid, point_to_metric  # noqa: E402
from src.mask import (  # noqa: E402
    blocked_mask,
    nearest_free_cell,
    restricted_mask,
    validate_path,
)
from src.metrics import route_metrics  # noqa: E402
from src.risk import exposure_surface, normalize_population  # noqa: E402
from src.router import plan_route_weighted  # noqa: E402

SHIFTS = [(i * 0.5, j * 0.5) for i in (-1, 0, 1) for j in (-1, 0, 1)]


def route_hash(cells: tuple[tuple[int, int], ...]) -> str:
    payload = b"".join(int(r).to_bytes(2, "little") + int(c).to_bytes(2, "little")
                       for r, c in cells)
    return hashlib.sha1(payload).hexdigest()[:10]


def shift_point(cfg, lon: float, lat: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    """把经纬度点按米整体平移，返回新经纬度。"""
    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)
    x, y = point_to_metric(cfg, lon, lat)
    new_lon, new_lat = to_geo.transform(x + dx_m, y + dy_m)
    return float(new_lon), float(new_lat)


def main() -> int:
    ap = argparse.ArgumentParser(description="③ 起点平移敏感性（吸附偏移）")
    ap.add_argument("--config", default=None)
    ap.add_argument("--cells", default="100,200,400")
    ap.add_argument("--out-csv", default="results/origin_shift.csv")
    ap.add_argument("--out-summary", default="results/origin_shift_summary.csv")
    ap.add_argument("--out-fig", default="figures/08_origin_shift.png")
    args = ap.parse_args()

    cfg0 = load_config(args.config)
    tif = pick_population_path(cfg0)
    cell_list = [int(x) for x in args.cells.split(",") if x.strip()]
    od = cfg0.od_pairs[0]
    rows: list[dict] = []
    summaries: list[dict] = []
    panels: list[dict] = []

    for cell_m in cell_list:
        t0 = time.perf_counter()
        cfg = replace(cfg0, grid=replace(cfg0.grid, cell_size_m=cell_m))
        grid = build_grid(cfg)
        pop = aggregate_population_to_grid(tif, grid, cfg)
        pop_norm, _ = normalize_population(pop, cfg.risk.population_percentile)
        exposure = exposure_surface(pop_norm, cfg.risk, altitude_m=cfg.grid.altitudes_m[0])
        blocked = blocked_mask(cfg, grid)
        restricted = restricted_mask(cfg, grid)
        graph = build_graph(grid, blocked, cfg.grid.connectivity)

        cell_rows: list[dict] = []
        for di, dj in SHIFTS:
            dx, dy = di * cell_m, dj * cell_m
            lon0, lat0 = shift_point(cfg, od.origin[0], od.origin[1], dx, dy)
            lon1, lat1 = shift_point(cfg, od.destination[0], od.destination[1], dx, dy)
            s = nearest_free_cell(cfg, grid, blocked, lon0, lat0)
            d = nearest_free_cell(cfg, grid, blocked, lon1, lat1)
            start, goal = (s.row, s.col), (d.row, d.col)
            for lam in (0.0, 1.0):
                route = plan_route_weighted(graph, grid, start, goal, exposure, lam)
                check = validate_path(list(route.cells), grid, cfg, blocked=blocked)
                m = route_metrics(graph, route.cells, exposure, pop=pop, cell_m=cell_m)
                row = {
                    "cell_m": cell_m,
                    "shift_dx_cells": di,
                    "shift_dy_cells": dj,
                    "shift_dx_m": round(dx, 1),
                    "shift_dy_m": round(dy, 1),
                    "shift_norm_m": round(float(np.hypot(dx, dy)), 1),
                    "lambda": lam,
                    "snap_start_m": round(float(s.offset_m), 1),
                    "snap_goal_m": round(float(d.offset_m), 1),
                    "length_km": round(m["length_m"] / 1000.0, 3),
                    "c_proxy_m": round(m["c_proxy_m"], 1),
                    "intensity": round(m["intensity"], 4),
                    "density_km2": round(m["density_km2"], 1),
                    "detour_ratio": round(route.detour_ratio, 4),
                    "restricted_cells": int(sum(bool(restricted[r, c]) for r, c in route.cells)),
                    "n_cells": len(route.cells),
                    "hard_crossings": check.crossings,
                    "valid": bool(check.ok),
                    "route_hash": route_hash(route.cells),
                }
                cell_rows.append(row)
                rows.append(row)

        df = pd.DataFrame(cell_rows)
        base = df[(df.shift_dx_cells == 0) & (df.shift_dy_cells == 0)].set_index("lambda")
        for lam in (0.0, 1.0):
            sub = df[df["lambda"] == lam]
            b = base.loc[lam]
            d_len = (sub["length_km"] / b["length_km"] - 1.0) * 100.0
            d_c = (sub["c_proxy_m"] / b["c_proxy_m"] - 1.0) * 100.0
            summaries.append({
                "cell_m": cell_m,
                "lambda": lam,
                "base_length_km": round(float(b["length_km"]), 3),
                "base_c_proxy_m": round(float(b["c_proxy_m"]), 1),
                "length_km_min": round(float(sub["length_km"].min()), 3),
                "length_km_max": round(float(sub["length_km"].max()), 3),
                "max_abs_delta_len_pct": round(float(d_len.abs().max()), 3),
                "c_proxy_m_min": round(float(sub["c_proxy_m"].min()), 1),
                "c_proxy_m_max": round(float(sub["c_proxy_m"].max()), 1),
                "max_abs_delta_c_pct": round(float(d_c.abs().max()), 3),
                "intensity_min": round(float(sub["intensity"].min()), 4),
                "intensity_max": round(float(sub["intensity"].max()), 4),
                "n_distinct_routes": int(sub["route_hash"].nunique()),
                "max_snap_m": round(float(sub[["snap_start_m", "snap_goal_m"]].max().max()), 1),
                "all_valid": bool(sub["valid"].all() and (sub["hard_crossings"] == 0).all()),
            })
        panels.append({"cell_m": cell_m, "df": df, "base": base})
        elapsed = time.perf_counter() - t0
        s0 = summaries[-2]
        print(f"{cell_m:>3d} m: λ=0 长度 {s0['length_km_min']}–{s0['length_km_max']} km "
              f"(最大偏 {s0['max_abs_delta_len_pct']:.2f}%) · "
              f"C {s0['c_proxy_m_min']}–{s0['c_proxy_m_max']} 代理·米 "
              f"(最大偏 {s0['max_abs_delta_c_pct']:.2f}%) · "
              f"不同路线 {s0['n_distinct_routes']} 条 · 用时 {elapsed:.1f} s")

    df_all = pd.DataFrame(rows)
    out_csv = cfg0.resolve(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(out_csv, index=False, encoding="utf-8")
    df_sum = pd.DataFrame(summaries)
    df_sum.to_csv(cfg0.resolve(args.out_summary), index=False, encoding="utf-8")

    # ---- 图：Δ长度 vs ΔC ----
    fig, axes = plt.subplots(1, len(panels), figsize=(4.9 * len(panels), 4.6), dpi=300,
                             squeeze=False)
    for ax, panel in zip(axes[0], panels):
        df = panel["df"]
        marks = {0.0: ("#1f77b4", "o", "λ=0 最短路"), 1.0: ("#d62728", "s", "λ=1 暴露加权")}
        for lam, (color, marker, label) in marks.items():
            sub = df[df["lambda"] == lam]
            b = panel["base"].loc[lam]
            dx = (sub["length_km"] / b["length_km"] - 1.0) * 100.0
            dy = (sub["c_proxy_m"] / b["c_proxy_m"] - 1.0) * 100.0
            ax.scatter(dx, dy, s=46, color=color, marker=marker, alpha=0.8,
                       edgecolor="black", linewidth=0.3, label=label, zorder=3)
        ax.axhline(0, color="gray", lw=0.8, ls="--")
        ax.axvline(0, color="gray", lw=0.8, ls="--")
        ax.set_xlabel("路线长度变化（%，相对不平移）")
        ax.set_ylabel("等效暴露长度 C 变化（%）")
        ax.set_title(f"{panel['cell_m']} m 网格（9 个平移位置）", fontsize=10.5)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7.5, loc="best")
        lim = max(abs(ax.get_xlim()[0]), abs(ax.get_xlim()[1]),
                  abs(ax.get_ylim()[0]), abs(ax.get_ylim()[1])) * 1.05
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
    fig.suptitle("核心 OD：起终点整体平移 ±0.5 格对结果的影响（吸附偏移敏感性）", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out_fig = cfg0.resolve(args.out_fig)
    out_fig.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fig)
    plt.close(fig)

    n_bad = int((~df_all["valid"]).sum() + (df_all["hard_crossings"] != 0).sum())
    print(f"表：{out_csv}")
    print(f"汇总：{cfg0.resolve(args.out_summary)}")
    print(f"图：{out_fig}（无效/穿越 {n_bad}）")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
