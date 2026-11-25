"""Day 6 入口：网格分辨率敏感性（100 / 200 / 400 m）。

同一 AOI、同一合成人口栅格、同一核心 OD，只改网格边长：
重采样人口 → 暴露代理 → 硬掩膜 → 建图 → 跑 λ=0 与 λ=1 两条路线。

重点看三件事：
1. 路线长度和绕行率是否随分辨率剧烈变化；
2. 「人群加权长度」Σ(人口×边长) 是否稳定（跨分辨率可比的近似量）；
3. 200 m 是不是合理折中（100 m 更细但更慢，400 m 可能漏掉狭窄通道）。

输出：
    results/resolution.csv    各分辨率指标
    figures/06_resolution.png 三条路线的并排对比
"""
from __future__ import annotations

import argparse
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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MplPolygon
from pyproj import Transformer

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402
from src.data import aggregate_population_to_grid, pick_population_path  # noqa: E402
from src.graph import build_graph, graph_stats  # noqa: E402
from src.grid import build_grid, edges_to_lonlat  # noqa: E402
from src.mask import (  # noqa: E402
    blocked_mask,
    nearest_free_cell,
    restricted_mask,
    validate_path,
    zone_geometries,
)
from src.risk import exposure_surface, normalize_population  # noqa: E402
from src.router import plan_route_weighted, route_exposure_m  # noqa: E402


def pop_weighted_length(graph, cells, pop, cell_m) -> float:
    """沿路线的平均人口密度（人/km²），跨分辨率可比。

    每格人口 ÷ 格面积 得到密度；按边长加权平均。若直接用「每格人口×边长」，
    会随网格变大而线性放大（每格人口按面积增长），不能跨分辨率比较。
    """
    area_m2 = float(cell_m) ** 2
    num = 0.0
    den = 0.0
    for a, b in zip(cells, cells[1:]):
        seg = float(graph.edges[a, b]["length_m"])
        dens = 0.5 * (float(pop[a]) + float(pop[b])) / area_m2
        num += dens * seg
        den += seg
    return (num / den) * 1e6 if den > 0 else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 6：网格分辨率敏感性")
    ap.add_argument("--config", default=None)
    ap.add_argument("--cells", default="100,200,400")
    ap.add_argument("--lambda", dest="lam", type=float, default=1.0)
    ap.add_argument("--out-csv", default="results/resolution.csv")
    ap.add_argument("--out-fig", default="figures/06_resolution.png")
    args = ap.parse_args()

    cfg0 = load_config(args.config)
    tif = pick_population_path(cfg0)
    cells_list = [int(x) for x in args.cells.split(",") if x.strip()]
    od = cfg0.od_pairs[0]
    rows: list[dict] = []
    panels: list[dict] = []

    for cell_m in cells_list:
        t0 = time.perf_counter()
        cfg = replace(cfg0, grid=replace(cfg0.grid, cell_size_m=cell_m))
        grid = build_grid(cfg)
        pop = aggregate_population_to_grid(tif, grid, cfg)
        pop_norm, p95 = normalize_population(pop, cfg.risk.population_percentile)
        exposure = exposure_surface(pop_norm, cfg.risk, altitude_m=cfg.grid.altitudes_m[0])
        blocked = blocked_mask(cfg, grid)
        restricted = restricted_mask(cfg, grid)
        graph = build_graph(grid, blocked, cfg.grid.connectivity)
        stats = graph_stats(graph)

        s = nearest_free_cell(cfg, grid, blocked, *od.origin)
        d = nearest_free_cell(cfg, grid, blocked, *od.destination)
        start, goal = (s.row, s.col), (d.row, d.col)
        base = plan_route_weighted(graph, grid, start, goal, exposure, lam=0.0)
        wtd = plan_route_weighted(graph, grid, start, goal, exposure, lam=args.lam)
        check0 = validate_path(list(base.cells), grid, cfg, blocked=blocked)
        check1 = validate_path(list(wtd.cells), grid, cfg, blocked=blocked)
        expo0 = route_exposure_m(graph, base.cells, exposure)
        expo1 = route_exposure_m(graph, wtd.cells, exposure)
        pw0 = pop_weighted_length(graph, base.cells, pop, cell_m)
        pw1 = pop_weighted_length(graph, wtd.cells, pop, cell_m)
        elapsed = time.perf_counter() - t0
        rows.append({
            "cell_m": cell_m,
            "rows": grid.rows,
            "cols": grid.cols,
            "n_cells": grid.rows * grid.cols,
            "nodes": stats["nodes"],
            "edges": stats["edges"],
            "blocked_cells": int(blocked.sum()),
            "restricted_cells": int(restricted.sum()),
            "p95_pop": round(float(p95), 2),
            "snap_start_m": round(s.offset_m, 1),
            "snap_goal_m": round(d.offset_m, 1),
            "length_km_l0": round(base.length_m / 1000.0, 3),
            "length_km_l1": round(wtd.length_m / 1000.0, 3),
            "delta_pct": round((wtd.length_m / base.length_m - 1.0) * 100.0, 3),
            "c_proxy_km_l0": round(expo0 / 1000.0, 3),
            "c_proxy_km_l1": round(expo1 / 1000.0, 3),
            "density_l0_km2": round(pw0, 1),
            "density_l1_km2": round(pw1, 1),
            "detour_l0": round(base.detour_ratio, 4),
            "detour_l1": round(wtd.detour_ratio, 4),
            "hard_crossings": check0.crossings + check1.crossings,
            "valid": bool(check0.ok and check1.ok),
        })
        panels.append({"cell_m": cell_m, "grid": grid, "pop": pop, "base": base,
                       "wtd": wtd, "exposure": exposure})
        print(f"{cell_m:>3d} m: {grid.cols}×{grid.rows} 格 · {stats['nodes']:,} 节点 · "
              f"λ=0 {base.length_m/1000:.3f} km → λ={args.lam:g} {wtd.length_m/1000:.3f} km "
              f"({rows[-1]['delta_pct']:+.2f}%) · 沿路平均人口密度 {pw1:,.0f} 对比 "
              f"{pw0:,.0f} 人/km² · 用时 {elapsed:.1f} s")

    df = pd.DataFrame(rows)
    out_csv = cfg0.resolve(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")

    # ---- 并排图 ----
    n = len(panels)
    fig, axes = plt.subplots(1, n, figsize=(5.2 * n, 5.4), dpi=300, squeeze=False)
    to_geo = Transformer.from_crs(cfg0.crs_metric, cfg0.crs_input, always_xy=True)
    minx, miny, maxx, maxy = cfg0.bbox
    last_ax = None
    for ax, panel in zip(axes[0], panels):
        grid, pop = panel["grid"], panel["pop"]
        lon_e, lat_e = edges_to_lonlat(grid, cfg0.crs_input)
        mesh = ax.pcolormesh(lon_e, lat_e, np.log10(pop + 1.0), cmap="magma", shading="flat")
        mesh.set_clip_path(MplPolygon(
            [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)],
            closed=True, transform=ax.transData))
        for z, (_, geom) in zip(cfg0.no_fly, zone_geometries(cfg0)):
            xs, ys = np.asarray(geom.exterior.coords).T
            lons, lats = to_geo.transform(xs, ys)
            if z.hard:
                ax.add_patch(MplPolygon(np.column_stack([lons, lats]), closed=True,
                                        facecolor="white", alpha=0.25, edgecolor="white",
                                        lw=1.2, ls="--", zorder=3))
            else:
                ax.plot(lons, lats, color="#ff4d4d", lw=1.2, ls="--", zorder=3)
        for route, color, label in ((panel["base"], "#00e5ff", "λ=0"),
                                    (panel["wtd"], "#ff3df0", f"λ={args.lam:g}")):
            xs = [float(grid.xs[c]) for _, c in route.cells]
            ys = [float(grid.ys[r]) for r, _ in route.cells]
            lons, lats = to_geo.transform(xs, ys)
            ax.plot(lons, lats, color="black", lw=3.6, solid_capstyle="round", zorder=5)
            ax.plot(lons, lats, color=color, lw=2.0, solid_capstyle="round", zorder=6,
                    label=label)
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_aspect(1.0 / max(np.cos(np.radians(float(np.mean(lat_e)))), 1e-6))
        ax.set_title(f"{panel['cell_m']} m 网格 · λ=0 {panel['base'].length_m/1000:.2f} km / "
                     f"λ={args.lam:g} {panel['wtd'].length_m/1000:.2f} km", fontsize=10)
        ax.set_xlabel("经度 (°E)")
        if ax is axes[0][0]:
            ax.set_ylabel("纬度 (°N)")
        last_ax = ax
    handles = [
        Line2D([], [], color="#00e5ff", lw=2.4, label="λ=0 最短路"),
        Line2D([], [], color="#ff3df0", lw=2.4, label=f"λ={args.lam:g} 暴露加权"),
        Patch(facecolor="white", alpha=0.5, edgecolor="white", ls="--", label="硬禁飞（示意）"),
        Line2D([], [], color="#ff4d4d", lw=1.2, ls="--", label="机场净空区（硬禁飞）"),
    ]
    last_ax.legend(handles=handles, loc="lower left", fontsize=7.5, framealpha=0.9)
    fig.suptitle("核心 OD：网格分辨率敏感性（同一人口栅格，100/200/400 m）", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out_fig = cfg0.resolve(args.out_fig)
    out_fig.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fig)
    plt.close(fig)

    n_bad = int((~df["valid"]).sum() + (df["hard_crossings"] != 0).sum())
    print(f"表：{out_csv}")
    print(f"图：{out_fig}（无效 {n_bad}）")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
