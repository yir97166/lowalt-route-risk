"""② Pareto 明细与去重规则。

审核意见：λ 扫描只说了「核心 OD 只有 3 个不同解」，没有 3 条路线的明细表，
也没写「什么算同一个解」。

做法：
1. 对每组 OD 以 λ=0–2、步长 0.025（81 档）重扫；
2. 按**格心序列哈希**去重：同一串 cells 视为同一个解，不论在多少个 λ 下出现；
3. 给每个解记「首次出现 λ / 最后出现 λ / 占多少档 / L / C / E / 绕行率 / 净空区内格数」；
4. 相邻不同解之间记切换阈值（新解首次出现的 λ）。

输出：
    results/pareto_routes.csv       每个 OD 的每个不同解（含明细）
    results/pareto_transitions.csv  λ 切换点
    figures/09_pareto_routes.png    核心 OD 的 3 条路线 + 解的分布
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
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
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.grid import build_grid, edges_to_lonlat  # noqa: E402
from src.mask import (  # noqa: E402
    blocked_mask,
    feasible_od,
    nearest_free_cell,
    restricted_mask,
    validate_path,
    zone_geometries,
)

MAX_SNAP_M = 300.0
from src.metrics import route_metrics  # noqa: E402
from src.router import plan_route_weighted, route_exposure_m  # noqa: E402

SHORT_NAMES = {
    "luohu_to_futian": "罗湖—福田",
    "futian_to_luohu": "福田—罗湖",
    "north_station_to_futian": "北站—福田",
    "longhua_to_futian": "龙华—福田",
    "buji_to_luohu": "布吉—罗湖",
    "north_station_to_shenzhen_bay": "北站—深圳湾",
    "futian_cbd_to_airport_east": "福田—机场东",
    "nanshan_to_baoan": "南山—宝安",
    "baoan_center_to_nanshan": "宝安—南山"
}


def short_label(od) -> str:
    base = SHORT_NAMES.get(od.name, od.name)
    if od.role == "core":
        return base + "（核心）"
    if od.role == "infeasible_example":
        return base + "（不可达）"
    return base

DEDUP_RULE = ("同一 OD 下，两条路线若格心序列完全相同（逐格相同，含起终点格），"
              "视为同一个解；等长但格心序列不同的算两个解（等长解）。")


def route_hash(cells: tuple[tuple[int, int], ...]) -> str:
    payload = b"".join(int(r).to_bytes(2, "little") + int(c).to_bytes(2, "little")
                       for r, c in cells)
    return hashlib.sha1(payload).hexdigest()[:10]


def main() -> int:
    ap = argparse.ArgumentParser(description="② Pareto 明细与去重")
    ap.add_argument("--config", default=None)
    ap.add_argument("--core-step", type=float, default=0.025)
    ap.add_argument("--other-step", type=float, default=0.05)
    ap.add_argument("--out-csv", default="results/pareto_routes.csv")
    ap.add_argument("--out-trans", default="results/pareto_transitions.csv")
    ap.add_argument("--out-fig", default="figures/09_pareto_routes.png")
    args = ap.parse_args()

    cfg = load_config(args.config)
    grid = build_grid(cfg)
    blocked = blocked_mask(cfg, grid)
    restricted = restricted_mask(cfg, grid)
    graph = build_graph(grid, blocked, cfg.grid.connectivity)
    pop, exposure = load_grid_arrays(cfg, grid)
    print(f"{grid.cols}×{grid.rows} 格 · {graph.number_of_nodes():,} 节点 · 去重规则：{DEDUP_RULE}")

    route_rows: list[dict] = []
    sweep_all: list[dict] = []
    trans_rows: list[dict] = []
    panels: list[dict] = []
    total_bad = 0
    t0 = time.perf_counter()

    for idx, od in enumerate(cfg.od_pairs):
        step = args.core_step if idx == 0 else args.other_step
        lambdas = np.round(np.arange(0.0, 2.0 + 1e-9, step), 3)
        s, d, feasible = feasible_od(cfg, grid, blocked, od, MAX_SNAP_M)
        if not feasible:
            print(f"{od.name}: 端点落在硬禁飞区内，跳过")
            continue
        start, goal = (s.row, s.col), (d.row, d.col)

        seq: list[dict] = []
        sweep: list[dict] = []
        n_bad = 0
        for lam in lambdas:
            route = plan_route_weighted(graph, grid, start, goal, exposure, lam)
            check = validate_path(list(route.cells), grid, cfg, blocked=blocked)
            n_bad += int(check.crossings) + (0 if check.ok else 1)
            h = route_hash(tuple(route.cells))
            seq.append({"lambda": float(lam), "cells": tuple(route.cells), "hash": h})
            sweep_all.append({"od": od.name, "lambda": float(lam),
                          "length_km": round(route.length_m / 1000.0, 3),
                          "c_proxy_m": round(route_exposure_m(graph, route.cells, exposure), 1),
                          "route_hash": h})

        # 按首次出现顺序编号
        order: list[str] = []
        by_hash: dict[str, dict] = {}
        for item in seq:
            h = item["hash"]
            if h not in by_hash:
                order.append(h)
                by_hash[h] = {"cells": item["cells"], "lambdas": []}
            by_hash[h]["lambdas"].append(item["lambda"])

        # 按目标值 (长度, C) 合并：不同格心序列但目标值相同的解算同一个解
        hash_metrics = {}
        for h in order:
            cells = by_hash[h]["cells"]
            m = route_metrics(graph, cells, exposure, pop=pop, cell_m=grid.cell_m)
            hash_metrics[h] = {
                "length_km": round(m["length_m"] / 1000.0, 3),
                "c_proxy_m": round(m["c_proxy_m"], 1),
                "metrics": m,
            }

        obj_order: list[tuple[float, float]] = []
        by_obj: dict[tuple[float, float], dict] = {}
        for h in order:
            key = (hash_metrics[h]["length_km"], hash_metrics[h]["c_proxy_m"])
            if key not in by_obj:
                obj_order.append(key)
                by_obj[key] = {"hashes": [], "lambdas": []}
            by_obj[key]["hashes"].append(h)
            by_obj[key]["lambdas"] += by_hash[h]["lambdas"]

        for rid, key in enumerate(obj_order, start=1):
            info = by_obj[key]
            h = info["hashes"][0]
            cells = by_hash[h]["cells"]
            m = hash_metrics[h]["metrics"]
            route = plan_route_weighted(graph, grid, start, goal, exposure, info["lambdas"][0])
            lams = info["lambdas"]
            route_rows.append({
                "od": od.name,
                "od_short": short_label(od),
                "route_id": rid,
                "first_lambda": float(min(lams)),
                "last_lambda": float(max(lams)),
                "n_lambda_slots": len(lams),
                "share_pct": round(len(lams) / len(lambdas) * 100.0, 1),
                "length_km": hash_metrics[h]["length_km"],
                "c_proxy_m": hash_metrics[h]["c_proxy_m"],
                "intensity": round(m["intensity"], 4),
                "density_km2": round(m["density_km2"], 1),
                "detour_ratio": round(route.detour_ratio, 4),
                "restricted_cells": int(sum(bool(restricted[r, c]) for r, c in cells)),
                "n_cells": len(cells),
                "route_hash": h,
            })

        for a, b in zip(obj_order, obj_order[1:]):
            first_b = min(by_obj[b]["lambdas"])
            trans_rows.append({
                "od": od.name,
                "od_short": short_label(od),
                "from_route": obj_order.index(a) + 1,
                "to_route": obj_order.index(b) + 1,
                "swap_at_lambda": float(first_b),
                "swap_at_lambda_prev": float(first_b - step),
            })
        panels.append({"od": od.name, "cells_by_route": [
            (i + 1, by_hash[by_obj[k]["hashes"][0]]["cells"]) for i, k in enumerate(obj_order)]})
        total_bad += n_bad
        print(f"{od.name}: {len(lambdas)} 档 λ · {len(obj_order)} 个不同解（按长度/C 合并） · "
              f"切换点 {[t['swap_at_lambda'] for t in trans_rows if t['od'] == od.name]} · "
              f"穿越/无效 {n_bad}")
        print(f"{od.name}: {len(lambdas)} 档 λ · {len(order)} 个不同解 · "
              f"切换点 {[t['swap_at_lambda'] for t in trans_rows if t['od'] == od.name]} · "
              f"穿越/无效 {n_bad}")

    df = pd.DataFrame(route_rows)
    out_csv = cfg.resolve(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    df_t = pd.DataFrame(trans_rows)
    df_t.to_csv(cfg.resolve(args.out_trans), index=False, encoding="utf-8")
    df_s = pd.DataFrame(sweep_all)
    df_s.to_csv(cfg.resolve("results/pareto_sweep_full.csv"), index=False, encoding="utf-8")
    print(f"全量扫描：{len(df_s)} 行 -> results/pareto_sweep_full.csv")

    # ---- 图：核心 OD 的三条路线 + 解分布 ----
    core_name = cfg.od_pairs[0].name
    core_routes = df[df["od"] == core_name].sort_values("route_id")
    core_cells = panels[0]["cells_by_route"]
    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)
    lon_e, lat_e = edges_to_lonlat(grid, cfg.crs_input)
    minx, miny, maxx, maxy = cfg.bbox

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.6, 6.4), dpi=300,
                                   gridspec_kw={"width_ratios": [1.05, 1.0]})
    mesh = ax1.pcolormesh(lon_e, lat_e, np.log10(pop + 1.0), cmap="magma", shading="flat")
    mesh.set_clip_path(MplPolygon([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)],
                                  closed=True, transform=ax1.transData))
    for zone, (_, geom) in zip(cfg.no_fly, zone_geometries(cfg)):
        xs, ys = np.asarray(geom.exterior.coords).T
        lons, lats = to_geo.transform(xs, ys)
        if zone.hard:
            ax1.add_patch(MplPolygon(np.column_stack([lons, lats]), closed=True,
                                     facecolor="white", alpha=0.22, edgecolor="white",
                                     lw=1.1, ls="--", zorder=3))
        else:
            ax1.plot(lons, lats, color="#ff4d4d", lw=1.2, ls="--", zorder=3)

    colors = ["#00e5ff", "#ffd166", "#ff3df0", "#7bd389", "#c792ea"]
    for (rid, cells), c in zip(core_cells, colors):
        xs = [float(grid.xs[col]) for _, col in cells]
        ys = [float(grid.ys[row]) for row, _ in cells]
        lons, lats = to_geo.transform(xs, ys)
        row = core_routes[core_routes.route_id == rid].iloc[0]
        ax1.plot(lons, lats, color="black", lw=3.4, solid_capstyle="round", zorder=5)
        ax1.plot(lons, lats, color=c, lw=1.9, solid_capstyle="round", zorder=6,
                 label=f"解 {rid}：λ {row.first_lambda:g}–{row.last_lambda:g}"
                       f"（{row.length_km:.2f} km / C {row.c_proxy_m:,.0f}）")
    ax1.set_xlim(minx, maxx)
    ax1.set_ylim(miny, maxy)
    ax1.set_aspect(1.0 / max(np.cos(np.radians(float(np.mean(lat_e)))), 1e-6))
    ax1.set_title("核心 OD：λ 扫描得到的全部不同解", fontsize=11)
    ax1.set_xlabel("经度 (°E)")
    ax1.set_ylabel("纬度 (°N)")
    ax1.legend(fontsize=7.4, loc="lower left", framealpha=0.92)

    for name, sub in df.groupby("od_short"):
        ax2.plot(sub["length_km"], sub["c_proxy_m"], marker="o", ms=6, lw=1.3,
                 label=name, alpha=0.9)
        for _, r in sub.iterrows():
            ax2.annotate(f"{r.route_id}", (r.length_km, r.c_proxy_m),
                         textcoords="offset points", xytext=(5, 5), fontsize=7)
    ax2.set_xlabel("路线长度 L（km）")
    ax2.set_ylabel("等效暴露长度 C（代理·米）")
    ax2.set_title("5 组 OD：不同解的位置（点旁数字 = 解编号）", fontsize=11)
    ax2.grid(alpha=0.25)
    ax2.legend(fontsize=7.4, loc="upper left")
    handles = [
        Patch(facecolor="white", alpha=0.5, edgecolor="white", ls="--", label="硬禁飞（示意）"),
        Line2D([], [], color="#ff4d4d", lw=1.2, ls="--", label="机场净空区（硬禁飞）"),
    ]
    ax1.legend(handles=handles + ax1.get_legend_handles_labels()[0],
               fontsize=7.2, loc="lower left", framealpha=0.92)
    fig.suptitle("Pareto 明细：同一格心序列算同一个解，等长不同序列算两个解", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out_fig = cfg.resolve(args.out_fig)
    out_fig.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fig)
    plt.close(fig)

    elapsed = time.perf_counter() - t0
    print(f"完成：{len(df)} 个解 · {len(df_t)} 个切换点 · 用时 {elapsed:.1f} s · "
          f"穿越/无效 {total_bad}")
    print(f"表：{out_csv}")
    print(f"切换表：{cfg.resolve(args.out_trans)}")
    print(f"图：{out_fig}")
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
