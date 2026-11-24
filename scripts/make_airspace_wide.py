"""Day 15：宽幅空域图（米制坐标，完整显示机场净空安全区走廊）。

用途：正式报告里的「空域约束」总览图。AOI 只覆盖深圳中西部 25×19 km，
机场净空安全区走廊向西南延伸出 AOI；只看 AOI 只能看到一小段边界，
容易被误读为「机场在 AOI 外、与本研究无关」。本图把显示范围外扩到走廊完整范围。

坐标用 EPSG:32649（米），横纵比例一致，避免经纬度直接画图造成的形变。

输出：figures/13_airspace_wide.png（300 dpi）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# matplotlib 缓存目录（Windows 上 %LOCALAPPDATA% 可能不可写）
_MPL_CACHE = ROOT / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
if not os.environ.get("MPLCONFIGDIR"):
    os.environ["MPLCONFIGDIR"] = str(_MPL_CACHE)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Polygon as MplPolygon, Rectangle  # noqa: E402
from pyproj import Transformer  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

from src.config import load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.mask import zone_geometries  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _rings(geom) -> list[np.ndarray]:
    """返回多边形的外环/内环（米制坐标，单位 km）。"""
    if geom.geom_type == "Polygon":
        out = [np.asarray(geom.exterior.coords) / 1000.0]
        out += [np.asarray(r.coords) / 1000.0 for r in geom.interiors]
        return out
    if geom.geom_type == "MultiPolygon":
        out: list[np.ndarray] = []
        for g in geom.geoms:
            out.extend(_rings(g))
        return out
    raise TypeError(geom.geom_type)


def main() -> int:
    cfg = load_config()
    grid = build_grid(cfg)
    pop, _ = load_grid_arrays(cfg, grid)
    zones = zone_geometries(cfg)

    x = grid.x_edges / 1000.0
    y = grid.y_edges / 1000.0
    minx, miny, maxx, maxy = grid.bounds_metric()
    aoi = np.array([minx, miny, maxx, maxy]) / 1000.0

    fig, ax = plt.subplots(figsize=(13.2, 7.6), dpi=300)

    mesh = ax.pcolormesh(x, y, np.log10(pop + 1.0), shading="auto",
                         cmap="magma", zorder=1)
    cbar = fig.colorbar(mesh, ax=ax, fraction=0.026, pad=0.02)
    cbar.set_label("人口（每 200 m 格，log10 显示）", fontsize=9)

    # 净空安全区 + 两个示意硬禁飞多边形
    corridor_bounds = None
    for name, geom in zones:
        is_corridor = name == "szx_airport_protection_zone"
        color = "#d62728" if is_corridor else "#b2182b"
        if is_corridor:
            corridor_bounds = np.array(geom.bounds) / 1000.0
        for ring in _rings(geom):
            ax.add_patch(MplPolygon(
                ring, closed=True,
                facecolor=color, alpha=0.14 if is_corridor else 0.45,
                edgecolor=color, lw=2.0 if is_corridor else 1.1, ls="--",
                zorder=2 if is_corridor else 3,
            ))

    # AOI 边界
    ax.add_patch(Rectangle((aoi[0], aoi[1]), aoi[2] - aoi[0], aoi[3] - aoi[1],
                           fill=False, edgecolor="#222222", lw=1.5, zorder=4))

    # AOI 与净空走廊的重叠部分：加深颜色，避免「看起来不重叠」的误读
    from shapely.geometry import box as shapely_box
    aoi_poly = shapely_box(*grid.bounds_metric())
    for name, geom in zones:
        if name != "szx_airport_protection_zone":
            continue
        inter = geom.intersection(aoi_poly)
        if inter.is_empty:
            continue
        for ring in _rings(inter):
            ax.add_patch(MplPolygon(ring, closed=True, facecolor="#d62728",
                                    alpha=0.38, edgecolor="none", zorder=3))
    ax.annotate(
        "机场净空安全区走廊\n长 40 km × 宽 20 km，向西南延伸出 AOI",
        xy=(corridor_bounds[0] + 9.0, corridor_bounds[3] - 9.0),
        xytext=(corridor_bounds[0] + 1.5, corridor_bounds[3] - 1.5),
        fontsize=8.5, color="#8b1a1a", zorder=10,
        arrowprops=dict(arrowstyle="->", color="#8b1a1a", lw=1.0),
    )

    # 核心 OD 的 λ=1 路线（经纬度 -> 米制）
    path_csv = ROOT / "results" / "weighted_path.csv"
    if path_csv.is_file():
        p = pd.read_csv(path_csv)
        to_m = Transformer.from_crs(cfg.crs_input, cfg.crs_metric, always_xy=True)
        rx, ry = to_m.transform(p["lon"].to_numpy(), p["lat"].to_numpy())
        rx, ry = rx / 1000.0, ry / 1000.0
        ax.plot(rx, ry, color="#17becf", lw=2.4, zorder=7, solid_capstyle="round")
        ax.scatter([rx[0]], [ry[0]], marker="^", s=95, color="#2ca02c",
                   edgecolor="black", lw=0.6, zorder=8)
        ax.scatter([rx[-1]], [ry[-1]], marker="v", s=95, color="#1f77b4",
                   edgecolor="black", lw=0.6, zorder=8)
        ax.annotate("起点 罗湖", (rx[0], ry[0]), textcoords="offset points",
                    xytext=(8, 8), fontsize=9, zorder=9)
        ax.annotate("终点 福田", (rx[-1], ry[-1]), textcoords="offset points",
                    xytext=(8, -14), fontsize=9, zorder=9)

    # 显示范围：AOI ∪ 净空走廊，留少量边距
    xs = [aoi[0], aoi[2]]
    ys = [aoi[1], aoi[3]]
    if corridor_bounds is not None:
        xs.extend([corridor_bounds[0], corridor_bounds[2]])
        ys.extend([corridor_bounds[1], corridor_bounds[3]])
    ax.set_xlim(min(xs) - 1.0, max(xs) + 3.0)
    ax.set_ylim(min(ys) - 0.6, max(ys) + 0.6)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("东向坐标（km，EPSG:32649）")
    ax.set_ylabel("北向坐标（km，EPSG:32649）")
    ax.set_title(
        "空域约束宽幅视图：机场净空安全区（深公规〔2017〕3 号尺寸，按「严禁」作硬禁飞）与核心路线",
        fontsize=11.5,
    )
    ax.grid(alpha=0.15, zorder=0)

    handles = [
        Patch(facecolor="#b2182b", alpha=0.45, edgecolor="#b2182b", ls="--",
              label="硬禁飞区（示意多边形）"),
        Patch(facecolor="#d62728", alpha=0.12, edgecolor="#d62728", ls="--",
              label="机场净空安全区（硬禁飞，官方尺寸）"),
        Patch(facecolor="#d62728", alpha=0.38, edgecolor="none",
              label="AOI 内受净空约束部分（37.5%）"),
        Line2D([], [], color="#17becf", lw=2.4, label="核心 OD 路线（λ=1）"),
        Line2D([], [], color="#222222", lw=1.5, label="AOI 边界（25×19 km）"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8.5, framealpha=0.85)

    ax.text(
        0.99, 0.02,
        "净空安全区覆盖 AOI 4,706/12,544 格（37.5%）；硬禁飞合计 4,982 格（39.7%）\n"
        "机场周边 4 组 OD 的端点落在此区内，判「不可达」——净空区内不宜设起降点",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
        color="#333333",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                  alpha=0.88, edgecolor="#cccccc"),
        zorder=10,
    )
    fig.text(
        0.01, 0.005,
        "数据仅用于方法演示：人口为 WorldPop 2020 建模估计，禁飞区为示意或公开资料近似，不构成适航、许可或运行依据。",
        fontsize=7.5, color="#555555",
    )

    out = ROOT / "figures" / "13_airspace_wide.png"
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"图：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
