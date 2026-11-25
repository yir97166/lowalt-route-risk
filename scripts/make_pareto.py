"""Day 5 入口：λ 扫描与距离—暴露 Pareto 曲线。

对每组 OD 扫 λ = 0, 0.1, …, 2.0，记录路线长度与累计暴露，做非支配筛选。
核心 OD 出「长度 vs 暴露」散点 + Pareto 前沿；5 组 OD 同图看
「多走 x% 距离换 y% 暴露下降」是否成立。

输出：
    results/pareto.csv       每组 OD × 每个 λ 的长度、暴露、绕行率
    results/pareto_front.csv 非支配点
    figures/05_pareto.png    左：核心 OD 前沿；右：5 组 OD 权衡曲线
"""
from __future__ import annotations

import argparse
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

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.mask import blocked_mask, feasible_od, restricted_mask, validate_path  # noqa: E402
from src.router import pareto_mask, plan_route_weighted, route_exposure_m  # noqa: E402

MAX_SNAP_M = 300.0

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



def main() -> int:
    ap = argparse.ArgumentParser(description="Day 5：λ 扫描 + Pareto")
    ap.add_argument("--config", default=None)
    ap.add_argument("--lam-max", type=float, default=2.0)
    ap.add_argument("--lam-step", type=float, default=0.1)
    ap.add_argument("--out-csv", default="results/pareto.csv")
    ap.add_argument("--out-front", default="results/pareto_front.csv")
    ap.add_argument("--out-fig", default="figures/05_pareto.png")
    args = ap.parse_args()

    cfg = load_config(args.config)
    grid = build_grid(cfg)
    blocked = blocked_mask(cfg, grid)
    restricted = restricted_mask(cfg, grid)
    graph = build_graph(grid, blocked, cfg.grid.connectivity)
    pop, exposure = load_grid_arrays(cfg, grid)
    lambdas = np.round(np.arange(0.0, args.lam_max + 1e-9, args.lam_step), 2)
    print(f"图 {graph.number_of_nodes():,} 节点 · λ {len(lambdas)} 个（0–{args.lam_max:g}）")

    rows: list[dict] = []
    fronts: list[dict] = []
    per_od: dict[str, list[tuple[float, float, float]]] = {}
    t0 = time.perf_counter()

    for od in cfg.od_pairs:
        s, d, feasible = feasible_od(cfg, grid, blocked, od, MAX_SNAP_M)
        if not feasible:
            print(f"{od.name}: 端点落在硬禁飞区内，跳过（不参与 Pareto）")
            continue
        start, goal = (s.row, s.col), (d.row, d.col)
        base_len = None
        base_exp = None
        od_rows: list[dict] = []
        for lam in lambdas:
            route = plan_route_weighted(graph, grid, start, goal, exposure, lam)
            check = validate_path(list(route.cells), grid, cfg, blocked=blocked)
            expo = route_exposure_m(graph, route.cells, exposure)
            n_zone = int(sum(bool(restricted[r, c]) for r, c in route.cells))
            if base_len is None:
                base_len, base_exp = route.length_m, expo
            delta_pct = (route.length_m / base_len - 1.0) * 100.0
            exp_drop = (1.0 - expo / base_exp) * 100.0 if base_exp > 0 else 0.0
            od_rows.append({
                "od": od.name,
                "od_short": short_label(od),
                "lambda": float(lam),
                "length_m": round(route.length_m, 1),
                "length_km": round(route.length_m / 1000.0, 3),
                "c_proxy_m": round(expo, 1),
                "c_proxy_km": round(expo / 1000.0, 3),
                "delta_len_pct": round(delta_pct, 3),
                "exposure_drop_pct": round(exp_drop, 2),
                "detour_ratio": round(route.detour_ratio, 4),
                "restricted_cells": n_zone,
                "hard_crossings": check.crossings,
                "valid": check.ok,
                "n_cells": len(route.cells),
            })
        df_od = pd.DataFrame(od_rows)
        mask = pareto_mask(df_od["length_m"].to_numpy(), df_od["c_proxy_m"].to_numpy())
        for i, r in enumerate(od_rows):
            r["pareto"] = bool(mask[i])
        df_od["pareto"] = mask
        rows.extend(od_rows)
        for _, r in df_od[mask].iterrows():
            fronts.append({
                "od": r["od"], "lambda": r["lambda"], "length_km": r["length_km"],
                "c_proxy_km": r["c_proxy_km"], "detour_ratio": r["detour_ratio"],
            })
        per_od[short_label(od)] = list(zip(
            df_od["delta_len_pct"], df_od["exposure_drop_pct"], df_od["lambda"]))
        n_front = int(mask.sum())
        print(f"{od.name}: {len(df_od)} 个 λ · 前沿 {n_front} 点 · "
              f"长度 {df_od['length_km'].min():.3f}–{df_od['length_km'].max():.3f} km · "
              f"C {df_od['c_proxy_m'].min():.0f}–{df_od['c_proxy_m'].max():.0f} 代理·米")

    df = pd.DataFrame(rows)
    out_csv = cfg.resolve(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    df_front = pd.DataFrame(fronts)
    df_front.to_csv(cfg.resolve(args.out_front), index=False, encoding="utf-8")

    # ---- 图 ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.5, 6.6), dpi=300,
                                   gridspec_kw={"width_ratios": [1.15, 1.0]})
    core = df[df["od"] == cfg.od_pairs[0].name].sort_values("lambda")
    sc = ax1.scatter(core["length_km"], core["c_proxy_km"], c=core["lambda"],
                     cmap="viridis", s=42, edgecolor="black", linewidth=0.3, zorder=3)
    front = core[core["pareto"]].sort_values("length_km")
    ax1.plot(front["length_km"], front["c_proxy_km"], color="#d62728", lw=2.0,
             marker="o", ms=4, zorder=4, label="Pareto 非支配点")
    ax1.set_xlabel("路线长度（km）")
    ax1.set_ylabel("累计暴露（暴露值 × km）")
    ax1.set_title("核心 OD：λ 0→2 的长度—暴露分布", fontsize=12)
    cb = fig.colorbar(sc, ax=ax1, shrink=0.86, pad=0.02)
    cb.set_label("λ")
    ax1.grid(alpha=0.25)
    ax1.legend(loc="upper right", fontsize=9)
    for lam_mark in (0.0, 1.0, 2.0):
        row = core[np.isclose(core["lambda"], lam_mark)]
        if len(row):
            r = row.iloc[0]
            ax1.annotate(f"λ={lam_mark:g}", (r["length_km"], r["c_proxy_km"]),
                         textcoords="offset points", xytext=(6, 6), fontsize=8)

    for name, pts in per_od.items():
        pts = sorted(pts)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax2.plot(xs, ys, marker="o", ms=3, lw=1.4, label=name)
    ax2.axhline(0.0, color="gray", lw=0.8, ls="--")
    ax2.axvline(0.0, color="gray", lw=0.8, ls="--")
    ax2.set_xlabel("路线长度变化（%，相对 λ=0）")
    ax2.set_ylabel("累计暴露下降（%，相对 λ=0）")
    ax2.set_title("5 组 OD：多走距离换暴露下降", fontsize=12)
    ax2.grid(alpha=0.25)
    ax2.legend(fontsize=8, loc="lower right")
    ax2.text(0.02, 0.98, "左上 = 同距离更低暴露\n右下 = 用距离换暴露",
             transform=ax2.transAxes, va="top", fontsize=8, color="#555")

    fig.suptitle("人口暴露加权路径：λ 扫描与距离—暴露权衡（单层 60 m，合成人口，示意禁飞区）",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_fig = cfg.resolve(args.out_fig)
    out_fig.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fig)
    plt.close(fig)

    n_bad = int((df["hard_crossings"] != 0).sum() + (~df["valid"]).sum())
    n_moved = int((df["delta_len_pct"] > 1e-6).sum())
    elapsed = time.perf_counter() - t0
    print(f"完成：{len(df)} 条路线 · 用时 {elapsed:.1f} s · 长度有变化的 {n_moved} 条 · "
          f"穿越/无效 {n_bad}")
    print(f"表：{out_csv}")
    print(f"图：{out_fig}")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
