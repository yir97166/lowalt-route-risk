"""Day 11：高度层与机场净空安全区尺寸情景敏感性。

两个情景，都只做「如果……会怎样」的敏感性，不当结论：

1. 高度层 60 / 90 / 120 m：暴露面乘以 alt_factor（1.00 / 0.85 / 0.70）。
   由于暴露是均匀缩放，边权 ``length × (1 + λ·f·e)`` 等价于把 λ 换成 ``λ·f``，
   路线几何应当完全不变，只有「切换阈值」沿 λ 轴平移。本脚本用数值实验验证
   这一点，并给出平移后的阈值；不声称「高度越高越安全」。
2. 机场净空安全区尺寸：半宽与端外延伸同时乘 {0.5, 1.0, 1.5}，看不可通行格占比与
   机场向 OD 的可达性怎么变，用来回答「安全区尺寸假设有多敏感」。
   注：本模型把整条净空安全区当作一个主区（hard）；空域规划里的主区/副区细分尚未建模。

输出：
- ``results/scenario_altitude.csv``        每个 OD × 高度的切换点明细
- ``results/scenario_altitude_summary.csv`` 每个 OD × 高度的汇总
- ``results/scenario_safety_area.csv``     安全区尺寸倍数 × 覆盖率/可达性
- ``figures/11_altitude_scenario.png``
- ``figures/12_safety_area_scenario.png``
"""

from __future__ import annotations

import os
import sys
import zlib
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_cache = ROOT / ".cache" / "matplotlib"
_cache.mkdir(parents=True, exist_ok=True)
if not os.environ.get("MPLCONFIGDIR"):
    os.environ["MPLCONFIGDIR"] = str(_cache)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

from src.config import Config, load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.grid import build_grid, edges_to_lonlat  # noqa: E402
from src import mask as maskmod  # noqa: E402
from src.router import plan_route_weighted, route_exposure_m  # noqa: E402

LAMBDAS = np.round(np.arange(0.0, 2.0001, 0.025), 3)
ALTITUDES = [60, 90, 120]


def _cell_hash(cells) -> str:
    raw = ",".join(f"{r}:{c}" for r, c in cells)
    return f"{zlib.crc32(raw.encode()) & 0xffffffff:08x}"


def feasible_ods(cfg: Config) -> list:
    return [od for od in cfg.od_pairs if od.role in {"core", "batch"}]


def sweep(graph, grid, start, goal, exposure, lambdas=LAMBDAS) -> pd.DataFrame:
    rows = []
    for lam in lambdas:
        r = plan_route_weighted(graph, grid, start, goal, exposure, float(lam))
        rows.append(
            {
                "lam": float(lam),
                "length_m": float(r.length_m),
                "C_m": float(route_exposure_m(graph, r.cells, exposure)),
                "cells": tuple(r.cells),
            }
        )
    return pd.DataFrame(rows)


def transitions(df: pd.DataFrame) -> pd.DataFrame:
    """只保留路线序列发生变化的 λ。"""
    keep = [0]
    for i in range(1, len(df)):
        if df.loc[i, "cells"] != df.loc[i - 1, "cells"]:
            keep.append(i)
    out = df.iloc[keep].copy()
    out["cells_hash"] = [f"{zlib.crc32(','.join(f'{r}:{c}' for r, c in cells).encode()) & 0xffffffff:08x}" for cells in out["cells"]]
    out = out.drop(columns=["cells"])
    base_len = float(df.loc[0, "length_m"])
    out["is_real_detour"] = out["length_m"] > base_len + 1e-6
    out["length_km"] = (out["length_m"] / 1000.0).round(3)
    return out


def run_altitude(cfg, grid, graph, exposure, results_dir: Path):
    factors = cfg.risk.altitude_factor
    detail_parts, summary_rows = [], []
    for od in feasible_ods(cfg):
        s, g, ok = maskmod.feasible_od(cfg, grid, maskmod.blocked_mask(cfg, grid), od)
        if not ok:
            continue
        start, goal = (s.row, s.col), (g.row, g.col)
        baseline60 = None
        for alt in ALTITUDES:
            f = float(factors.get(alt, 1.0))
            exp_alt = exposure * f
            df = sweep(graph, grid, start, goal, exp_alt)
            tr = transitions(df)
            tr.insert(0, "altitude_m", alt)
            tr.insert(0, "od", od.name)
            detail_parts.append(tr)

            real = tr[tr["is_real_detour"]]
            first_real = float(real["lam"].iloc[0]) if len(real) else float("nan")
            any_change = tr[tr["lam"] > 0]
            first_change = float(any_change["lam"].iloc[0]) if len(any_change) else float("nan")
            row1 = df.iloc[(df["lam"] - 1.0).abs().idxmin()]
            base = df.iloc[0]
            if alt == 60:
                baseline60 = df
            # 验证：高度 f 在 λ 处的路线 = 60 m 在 λ·f 处的路线
            mismatch = 0
            comparable = 0
            if baseline60 is not None:
                for _, r in df.iterrows():
                    lam60 = min(float(r["lam"]) * f, 2.0)
                    j = int(np.argmin(np.abs(baseline60["lam"].to_numpy() - lam60)))
                    if abs(baseline60.iloc[j]["lam"] - lam60) < 1e-9:
                        comparable += 1
                        if baseline60.iloc[j]["cells"] != r["cells"]:
                            mismatch += 1
            summary_rows.append(
                {
                    "od": od.name,
                    "altitude_m": alt,
                    "alt_factor": f,
                    "solutions": int(len(tr)),
                    "first_change_lam": first_change,
                    "first_real_detour_lam": first_real,
                    "base_length_km": round(float(base["length_m"]) / 1000.0, 3),
                    "C0_m": round(float(base["C_m"]), 1),
                    "C_lam1_m": round(float(row1["C_m"]), 1),
                    "length_change_pct_lam1": round(
                        (float(row1["length_m"]) / float(base["length_m"]) - 1.0) * 100.0, 2
                    ),
                    "C_change_pct_lam1": round(
                        (float(row1["C_m"]) / float(base["C_m"]) - 1.0) * 100.0, 2
                    ),
                    "scaled_route_mismatch": mismatch,
                    "scaled_route_compared": comparable,
                }
            )
    detail = pd.concat(detail_parts, ignore_index=True)
    summary = pd.DataFrame(summary_rows)
    detail.to_csv(results_dir / "scenario_altitude.csv", index=False, encoding="utf-8")
    summary.to_csv(results_dir / "scenario_altitude_summary.csv", index=False, encoding="utf-8")
    return summary, detail


def _corridor(cfg: Config):
    for name, geom in maskmod.hard_zone_geometries(cfg):
        if name.startswith("szx"):
            return geom
    raise KeyError("szx_airport_protection_zone not found")


scaled_cfg = maskmod.scale_corridor


def run_buffer(cfg, grid, results_dir: Path) -> pd.DataFrame:
    factors = [0.5, 1.0, 1.5]
    rows = []
    airports = [od for od in cfg.od_pairs if od.role == "infeasible_example"]
    for fac in factors:
        c = scaled_cfg(cfg, fac)
        blocked = maskmod.blocked_mask(c, grid)
        corridor = _corridor(c)
        safety_area_cells = int(maskmod._mask_from_geometries(grid, [corridor]).sum())
        graph = build_graph(grid, blocked)
        core = next(od for od in cfg.od_pairs if od.role == "core")
        s, g, ok = maskmod.feasible_od(c, grid, blocked, core)
        core_len = None
        if ok:
            from src.router import plan_route

            r = plan_route(graph, grid, (s.row, s.col), (g.row, g.col))
            core_len = round(float(r.length_m) / 1000.0, 3)
        feas, offs = 0, []
        for od in airports:
            s2, g2, ok2 = maskmod.feasible_od(c, grid, blocked, od)
            maxoff = max(float(s2.offset_m), float(g2.offset_m))
            offs.append(maxoff)
            feas += int(ok2)
        rows.append(
            {
                "safety_area_factor": fac,
                "blocked_cells": int(blocked.sum()),
                "blocked_pct": round(float(blocked.mean()) * 100.0, 2),
                "safety_area_cells": safety_area_cells,
                "safety_area_pct": round(safety_area_cells / blocked.size * 100.0, 2),
                "core_reachable": bool(ok),
                "core_length_km": core_len,
                "airport_ods_feasible": feas,
                "airport_ods_total": len(airports),
                "airport_max_snap_m": round(float(max(offs)), 1) if offs else None,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(results_dir / "scenario_safety_area.csv", index=False, encoding="utf-8")
    return df


SHORT_CN = {
    "luohu_to_futian": "罗湖—福田",
    "futian_to_luohu": "福田—罗湖",
    "buji_to_luohu": "布吉—罗湖",
    "north_station_to_futian": "北站—福田",
    "longhua_to_futian": "龙华—福田",
}


def fig_altitude(summary: pd.DataFrame, detail: pd.DataFrame, out: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.0), constrained_layout=True)
    colors = {60: "#1f77b4", 90: "#ff7f0e", 120: "#2ca02c"}
    ax1.axhline(7.014, color="#999999", lw=0.8, ls=":")

    # 左：核心 OD 的长度阶梯，三档高度在 λ 轴上等比例右移
    for alt in ALTITUDES:
        d = detail[(detail["od"] == "luohu_to_futian") & (detail["altitude_m"] == alt)].sort_values("lam")
        if d.empty:
            continue
        xs = list(d["lam"]) + [2.0]
        ys = list(d["length_km"]) + [float(d["length_km"].iloc[-1])]
        ax1.step(xs, ys, where="post", color=colors[alt], lw=1.8, label=f"{alt} m")
        ax1.scatter(d["lam"], d["length_km"], s=16, color=colors[alt], zorder=3)
    ax1.set_xlabel("λ")
    ax1.set_ylabel("核心 OD 路线长度（km）")
    core = summary[summary["od"] == "luohu_to_futian"]
    th = {int(r["altitude_m"]): float(r["first_real_detour_lam"]) for _, r in core.iterrows()}
    ax1.set_title(f"核心 OD：阈值 {th.get(60, float('nan')):.3f} / {th.get(90, float('nan')):.3f} / {th.get(120, float('nan')):.3f}（比例 = 1/f）")
    ax1.set_xlim(0, 2.0)
    ax1.legend(fontsize=9, loc="lower right")
    ax1.grid(alpha=0.25)

    # 右：每个 OD 的首次真绕行阈值，按高度分组
    rows = [od for od in dict.fromkeys(summary["od"]) if summary[summary["od"] == od]["first_real_detour_lam"].notna().any()]
    width = 0.26
    for k, alt in enumerate(ALTITUDES):
        vals = []
        for od in rows:
            s = summary[(summary["od"] == od) & (summary["altitude_m"] == alt)]
            vals.append(float(s["first_real_detour_lam"].iloc[0]) if len(s) else float("nan"))
        y = np.arange(len(rows)) + (k - 1) * width
        ax2.barh(y, vals, height=width, color=colors[alt], label=f"{alt} m")
    ax2.set_yticks(np.arange(len(rows)))
    ax2.set_yticklabels([SHORT_CN.get(od, od) for od in rows], fontsize=9)
    ax2.set_xlabel("首次真绕行的 λ 阈值")
    ax2.set_title("阈值随高度等比例右移：λ* ∝ 1 / alt_factor")
    ax2.legend(fontsize=9)
    ax2.grid(axis="x", alpha=0.25)

    fig.suptitle("高度层情景敏感性（60 m 为基准；只作情景，不构成安全结论）", fontsize=12)
    fig.savefig(out, dpi=300)
    plt.close(fig)


def fig_buffer(cfg, grid, df: pd.DataFrame, out: Path) -> None:
    from matplotlib.patches import Polygon as MplPolygon
    from pyproj import Transformer

    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.2), constrained_layout=True)

    lon_edges, lat_edges = edges_to_lonlat(grid, cfg.crs_input)
    lon0, lon1 = float(lon_edges[0, 0]), float(lon_edges[-1, -1])
    lat_max, lat_min = float(lat_edges[0, 0]), float(lat_edges[-1, -1])
    ax1.add_patch(
        MplPolygon(
            [(lon0, lat_min), (lon1, lat_min), (lon1, lat_max), (lon0, lat_max)],
            closed=True, fill=False, edgecolor="#555555", lw=1.0,
        )
    )
    for fac, color in [(0.5, "#9467bd"), (1.0, "#d62728"), (1.5, "#2ca02c")]:
        c = scaled_cfg(cfg, fac)
        xs, ys = _corridor(c).exterior.xy
        lon, lat = to_geo.transform(np.asarray(xs), np.asarray(ys))
        ax1.plot(lon, lat, ls="--", lw=1.6, color=color, label=f"安全区 ×{fac}（安全区格 {df.set_index('safety_area_factor').loc[fac,'safety_area_cells']}）")
        if fac == 1.0:
            ax1.fill(lon, lat, color="#d62728", alpha=0.10)
    for od in cfg.od_pairs:
        if od.role != "core":
            continue
        ax1.scatter(*od.origin, marker="^", s=70, color="#2ca02c", zorder=4, label="起点 O（罗湖）")
        ax1.scatter(*od.destination, marker="v", s=70, color="#1f77b4", zorder=4, label="终点 D（福田）")
    ax1.set_xlim(cfg.bbox[0], cfg.bbox[2])
    ax1.set_ylim(cfg.bbox[1], cfg.bbox[3])
    ax1.set_xlabel("经度（°E）")
    ax1.set_ylabel("纬度（°N）")
    ax1.set_title("安全区尺寸情景：轮廓 ×0.5 / ×1.0 / ×1.5")
    ax1.legend(fontsize=8, loc="lower left")
    ax1.grid(alpha=0.2)

    ax2.bar(df["safety_area_factor"].astype(str), df["blocked_pct"], color="#d62728", alpha=0.85)
    for _, r in df.iterrows():
        ax2.text(
            str(r["safety_area_factor"]), r["blocked_pct"] + 0.6,
            f"{r['blocked_cells']} 格\n机场向可达 {int(r['airport_ods_feasible'])}/{int(r['airport_ods_total'])}",
            ha="center", fontsize=8,
        )
    ax2.set_xlabel("安全区尺寸倍数（半宽与端外延伸同乘）")
    ax2.set_ylabel("不可通行格占比（%）")
    ax2.set_title("安全区越大，机场向 OD 越不可达")
    ax2.set_ylim(0, max(df["blocked_pct"]) * 1.35)
    ax2.grid(axis="y", alpha=0.25)

    fig.suptitle("机场净空安全区尺寸敏感性（核心 OD 罗湖—福田不受影响）", fontsize=12)
    fig.savefig(out, dpi=300)
    plt.close(fig)


def main() -> int:
    cfg = load_config()
    grid = build_grid(cfg)
    pop, exposure = load_grid_arrays(cfg, grid)
    blocked = maskmod.blocked_mask(cfg, grid)
    graph = build_graph(grid, blocked)
    results_dir = cfg.resolve("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    summary, detail = run_altitude(cfg, grid, graph, exposure, results_dir)
    buffer_df = run_buffer(cfg, grid, results_dir)
    fig_altitude(summary, detail, cfg.resolve("figures/11_altitude_scenario.png"))
    fig_buffer(cfg, grid, buffer_df, cfg.resolve("figures/12_safety_area_scenario.png"))

    print("高度情景汇总：")
    print(summary.to_string(index=False))
    print("\n安全区尺寸情景汇总：")
    print(buffer_df.to_string(index=False))
    print("\n图：figures/11_altitude_scenario.png, figures/12_safety_area_scenario.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
