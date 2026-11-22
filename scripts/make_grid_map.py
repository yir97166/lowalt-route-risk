"""Day 2 入口：200 m 网格 + 禁飞硬掩膜 + 起终点吸附。

输出：
    figures/01_grid_nofly.png
    data/processed/od_snap.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 与 src/viz.py 相同：OneDrive / 非 ASCII 用户名下默认缓存目录可能不可写。
_MPL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
if not os.environ.get("MPLCONFIGDIR"):
    os.environ["MPLCONFIGDIR"] = str(_MPL_CACHE)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, Polygon as MplPolygon
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402
from src.grid import build_grid, edges_to_lonlat  # noqa: E402
from src.mask import (  # noqa: E402
    blocked_mask,
    feasible_od,
    zone_geometries,
)
from pyproj import Transformer  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 2：网格 + 禁飞硬掩膜")
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default="figures/01_grid_nofly.png")
    ap.add_argument("--snap-csv", default="data/processed/od_snap.csv")
    args = ap.parse_args()

    cfg = load_config(args.config)
    grid = build_grid(cfg)
    blocked = blocked_mask(cfg, grid)
    lon_e, lat_e = edges_to_lonlat(grid, cfg.crs_input)

    total = int(blocked.size)
    n_blocked = int(blocked.sum())
    print(f"网格：{grid.rows} 行 × {grid.cols} 列，共 {total:,} 格")
    print(f"禁飞硬掩膜：不可通行 {n_blocked:,} 格（{n_blocked / total:.2%}），"
          f"可通行 {total - n_blocked:,} 格")

    # 每个硬禁飞区单独统计
    from dataclasses import replace

    for zone in cfg.no_fly:
        if not zone.hard:
            continue
        single = blocked_mask(replace(cfg, no_fly=(zone,)), grid)
        print(f"  - {zone.name}: {int(single.sum()):,} 格")

    # 起终点吸附
    snap_rows = []
    for od in cfg.od_pairs:
        s_o, s_d, feasible = feasible_od(cfg, grid, blocked, od)
        snap_rows.append(
            dict(od=od.name, end="origin", row=s_o.row, col=s_o.col,
                 offset_m=round(s_o.offset_m, 1), lon=s_o.lon, lat=s_o.lat)
        )
        snap_rows.append(
            dict(od=od.name, end="destination", row=s_d.row, col=s_d.col,
                 offset_m=round(s_d.offset_m, 1), lon=s_d.lon, lat=s_d.lat)
        )
        for row in snap_rows[-2:]:
            row["feasible"] = bool(feasible)
        print(f"{od.name}: 起点吸附 {s_o.offset_m:.1f} m，终点吸附 {s_d.offset_m:.1f} m"
              + ("" if feasible else "  ← 端点落在硬禁飞区内，判不可达"))
    snap_df = pd.DataFrame(snap_rows)
    snap_path = cfg.resolve(args.snap_csv)
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    snap_df.to_csv(snap_path, index=False, encoding="utf-8")

    # 绘图
    fig, ax = plt.subplots(figsize=(11, 8.4), dpi=160)
    cmap = ListedColormap(["#f4f4f4", "#d73027"])
    mesh = ax.pcolormesh(lon_e, lat_e, blocked.astype(float), cmap=cmap, vmin=0, vmax=1,
                         shading="flat")
    minx, miny, maxx, maxy = cfg.bbox
    mesh.set_clip_path(MplPolygon(
        [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)],
        closed=True, transform=ax.transData))
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    # 网格线（200 m），裁到 AOI
    segs = []
    for j in range(lon_e.shape[1]):
        segs.append([(lon_e[0, j], lat_e[0, j]), (lon_e[-1, j], lat_e[-1, j])])
    for i in range(lon_e.shape[0]):
        segs.append([(lon_e[i, 0], lat_e[i, 0]), (lon_e[i, -1], lat_e[i, -1])])
    ax.add_collection(LineCollection(segs, colors="black", linewidths=0.15, alpha=0.18,
                                     zorder=1))

    # 空域约束：硬禁飞画边界，机场净空走廊画半透明覆盖
    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)

    def _ring(geom) -> np.ndarray:
        xs, ys = np.asarray(geom.exterior.coords).T
        lons, lats = to_geo.transform(xs, ys)
        return np.column_stack([lons, lats])

    for zone, (_, geom) in zip(cfg.no_fly, zone_geometries(cfg)):
        ring = _ring(geom)
        ax.add_patch(MplPolygon(ring, closed=True, fill=False, edgecolor="#b2182b",
                                lw=1.8, ls="--", zorder=4))

    # 起终点与吸附点
    core = cfg.od_pairs[0]
    ax.scatter(*core.origin, marker="^", s=170, c="#20d020", edgecolor="black", zorder=6)
    ax.scatter(*core.destination, marker="v", s=170, c="#2080ff", edgecolor="black", zorder=6)

    _OD_LABEL = {
        "luohu_to_futian": ("罗湖", "福田"),
        "north_station_to_shenzhen_bay": ("北站", "深圳湾"),
        "futian_cbd_to_airport_east": ("福田 CBD", "机场东"),
        "nanshan_to_baoan": ("南山", "宝安"),
        "baoan_center_to_nanshan": ("宝安中心", "南山"),
    }
    o_lab, d_lab = _OD_LABEL.get(core.name, ("O", "D"))

    handles = [
        Patch(facecolor="#d73027", label=f"硬禁飞格（{n_blocked:,}）"),
        Line2D([], [], color="#b2182b", lw=1.8, ls="--", label="禁飞边界（净空走廊为官方尺寸）"),
        Line2D([], [], marker="^", ls="", markersize=11, markerfacecolor="#20d020",
               markeredgecolor="black", label=f"起点 O（{o_lab}）"),
        Line2D([], [], marker="v", ls="", markersize=11, markerfacecolor="#2080ff",
               markeredgecolor="black", label=f"终点 D（{d_lab}）"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.92)
    ax.set_title(
        f"200 m 网格与空域约束\n"
        f"AOI {grid.cols}×{grid.rows} · 硬禁飞 {n_blocked:,} 格（{n_blocked / total:.2%}）"
        f" · 判定：格子与硬禁飞区有重叠即阻挡",
        fontsize=12.5,
    )
    ax.set_xlabel("经度 (°E)")
    ax.set_ylabel("纬度 (°N)")
    lat_mid = float(np.mean(lat_e))
    ax.set_aspect(1.0 / max(np.cos(np.radians(lat_mid)), 1e-6))
    ax.text(0.99, 0.01, "机场净空走廊按深公规〔2017〕3 号尺寸、作硬禁飞；两个多边形为手工示意",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="white",
            bbox=dict(boxstyle="round", fc="black", alpha=0.55, ec="none"))

    out = cfg.resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"图：{out}")
    print(f"吸附表：{snap_path}（{len(snap_df)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
