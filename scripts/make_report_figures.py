"""生成报告专用图：按最终印刷宽度（6.5 in，约 16.5 cm）设计，300 dpi。

与 figures/ 下的归档图不同，这里字号按 9–10 pt 设计；插入 Word 时按 16.4 cm
宽放置，缩放比≈1.0，字号不会被压小。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon, Rectangle  # noqa: E402
from pyproj import Transformer  # noqa: E402
from shapely.geometry import box as sbox  # noqa: E402

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 7.5,
    "axes.titlesize": 8,
    "axes.labelsize": 7.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "legend.frameon": False,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "figure.dpi": 150,
    "savefig.dpi": 600,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
})

from src.config import load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.mask import blocked_mask, feasible_od, zone_geometries  # noqa: E402
from src.router import plan_route, plan_route_weighted  # noqa: E402

OUT = ROOT / "figures" / "report"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#1F3864"
BLUE = "#0072B2"
CYAN = "#009E73"
MAGENTA = "#CC79A7"
RED = "#D55E00"
GREY = "#7F7F7F"


def _mesh_edges(grid, cfg):
    t = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)
    xe, ye = np.meshgrid(grid.x_edges, grid.y_edges)
    lon, lat = t.transform(xe, ye)
    return lon, lat


def fig_airspace(cfg, grid):
    zones = zone_geometries(cfg)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    aoi = [v / 1000.0 for v in grid.bounds_metric()]
    aoi_poly = sbox(*grid.bounds_metric())

    for name, geom in zones:
        xs, ys = geom.exterior.xy
        if name == "szx_airport_protection_zone":
            ax.add_patch(MplPolygon(list(zip([v / 1000 for v in xs], [v / 1000 for v in ys])),
                                    closed=True, facecolor=RED, alpha=0.10,
                                    edgecolor=RED, lw=1.0, ls="--", zorder=1))
            inter = geom.intersection(aoi_poly)
            for poly in getattr(inter, "geoms", [inter]):
                if poly.is_empty:
                    continue
                x2, y2 = poly.exterior.xy
                ax.add_patch(MplPolygon(list(zip([v / 1000 for v in x2], [v / 1000 for v in y2])),
                                        closed=True, facecolor=RED, alpha=0.28,
                                        edgecolor="none", zorder=2))
        else:
            ax.add_patch(MplPolygon(list(zip([v / 1000 for v in xs], [v / 1000 for v in ys])),
                                    closed=True, facecolor="#9CA3AF", alpha=0.55,
                                    edgecolor="#6B7280", lw=0.8, zorder=2))

    ax.add_patch(Rectangle((aoi[0], aoi[1]), aoi[2] - aoi[0], aoi[3] - aoi[1],
                           fill=False, edgecolor=NAVY, lw=1.3, zorder=3))

    core = next(od for od in cfg.od_pairs if od.role == "core")
    blocked = blocked_mask(cfg, grid)
    origin, dest, _ = feasible_od(cfg, grid, blocked, core)
    exposure = load_grid_arrays(cfg, grid)[1]
    route = plan_route_weighted(build_graph(grid, blocked), grid,
                                (origin.row, origin.col), (dest.row, dest.col),
                                exposure, 1.0)
    xs = [grid.xs[c] / 1000 for _, c in route.cells]
    ys = [grid.ys[r] / 1000 for r, _ in route.cells]
    ax.plot(xs, ys, color=CYAN, lw=2.2, zorder=5)
    ax.scatter([grid.xs[origin.col] / 1000], [grid.ys[origin.row] / 1000],
               marker="^", s=60, c="#2E7D32", edgecolors="white", zorder=6)
    ax.scatter([grid.xs[dest.col] / 1000], [grid.ys[dest.row] / 1000],
               marker="v", s=60, c=BLUE, edgecolors="white", zorder=6)
    ax.annotate("罗湖", (grid.xs[origin.col] / 1000, grid.ys[origin.row] / 1000),
                xytext=(6, -12), textcoords="offset points", fontsize=8)
    ax.annotate("福田", (grid.xs[dest.col] / 1000, grid.ys[dest.row] / 1000),
                xytext=(6, -12), textcoords="offset points", fontsize=8)

    ax.set_xlim(aoi[0] - 2, aoi[2] + 2)
    ax.set_ylim(aoi[1] - 2, aoi[3] + 2)
    ax.set_aspect("equal")
    ax.set_xlabel("东向坐标 (km)")
    ax.set_ylabel("北向坐标 (km)")
    ax.grid(alpha=0.15, lw=0.4)
    handles = [
        Line2D([], [], color=CYAN, lw=2.2, label="核心 OD 路线（λ=1）"),
        Rectangle((0, 0), 1, 1, facecolor=RED, alpha=0.25, edgecolor=RED,
                  ls="--", label="机场净空安全区（硬禁飞）"),
        Rectangle((0, 0), 1, 1, facecolor="#9CA3AF", alpha=0.6,
                  edgecolor=GREY, label="示意禁飞多边形"),
        Line2D([], [], color=NAVY, lw=1.3, label="AOI 边界"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=0.92)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_airspace.png", bbox_inches="tight")
    fig.savefig(OUT / "fig1_airspace.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_population(cfg, grid):
    pop, _ = load_grid_arrays(cfg, grid)
    lon, lat = _mesh_edges(grid, cfg)
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    mesh = ax.imshow(np.log10(pop + 1), cmap="magma", origin="upper",
                     extent=[lon.min(), lon.max(), lat.min(), lat.max()],
                     aspect="auto", interpolation="nearest")
    cb = fig.colorbar(mesh, ax=ax, pad=0.02)
    cb.set_label("人口（人/200 m 格，log10）", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    ax.set_xlabel("经度 (°E)")
    ax.set_ylabel("纬度 (°N)")
    ax.set_title("WorldPop 2020 人口，聚合到 200 m 网格", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_population.png", bbox_inches="tight")
    fig.savefig(OUT / "fig2_population.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_routes(cfg, grid):
    pop, exposure = load_grid_arrays(cfg, grid)
    lon, lat = _mesh_edges(grid, cfg)
    blocked = blocked_mask(cfg, grid)
    graph = build_graph(grid, blocked)
    core = next(od for od in cfg.od_pairs if od.role == "core")
    origin, dest, _ = feasible_od(cfg, grid, blocked, core)
    s, g = (origin.row, origin.col), (dest.row, dest.col)
    base = plan_route(graph, grid, s, g)
    wtd = plan_route_weighted(graph, grid, s, g, exposure, 1.0)
    trafo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)

    fig, ax = plt.subplots(figsize=(6.5, 4.3))
    ax.imshow(np.log10(pop + 1), cmap="Greys", origin="upper",
              extent=[lon.min(), lon.max(), lat.min(), lat.max()],
              aspect="auto", alpha=0.55, interpolation="nearest")
    for route, color, ls, label in (
        (base, CYAN, "-", f"最短路 7.01 km"),
        (wtd, MAGENTA, (0, (4, 2)), f"低暴露 7.51 km"),
    ):
        xs, ys = zip(*[(grid.xs[c], grid.ys[r]) for r, c in route.cells])
        lons, lats = trafo.transform(xs, ys)
        ax.plot(lons, lats, color=color, lw=2.0, ls=ls, label=label)
    ax.scatter([origin.lon], [origin.lat], marker="^", s=60, c="#2E7D32",
               edgecolors="white", zorder=5)
    ax.scatter([dest.lon], [dest.lat], marker="v", s=60, c=BLUE,
               edgecolors="white", zorder=5)
    ax.annotate("起点 罗湖", (origin.lon, origin.lat), xytext=(-6, 10), ha="right",
                textcoords="offset points", fontsize=8)
    ax.annotate("终点 福田", (dest.lon, dest.lat), xytext=(6, -14), ha="left",
                textcoords="offset points", fontsize=8)
    ax.set_xlabel("经度 (°E)")
    ax.set_ylabel("纬度 (°N)")
    ax.set_title("核心 OD：最短 vs 低暴露（λ=1）", fontsize=9)
    ax.legend(loc="upper left", frameon=True, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_routes.png", bbox_inches="tight")
    fig.savefig(OUT / "fig3_routes.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_pareto():
    df = pd.read_csv(ROOT / "results" / "pareto_routes.csv")
    df = df[df["od"] == "luohu_to_futian"].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6.5, 3.4))

    colors = ["#1f4e79", "#2a9d8f", "#e76f51"]
    names = ["λ=0：纯距离", "λ=0.025–0.80：等长低暴露", "λ=0.825–2.0：真绕行"]
    labels = [
        "7.014 km，C=3,922",
        "7.014 km，C=3,242（−17.4%）",
        "7.511 km，C=2,626（−33.1%）",
    ]
    for i, (_, r) in enumerate(df.iterrows()):
        ax.scatter(r["length_km"], r["c_proxy_m"], s=95, color=colors[i],
                   edgecolors="white", linewidths=1.0, zorder=3, label=names[i])
    ax.legend(loc="upper right", fontsize=7.5, frameon=True, framealpha=0.92)

    text_pos = [(7.055, 3900), (7.055, 3320), (7.20, 2570)]
    for i, ((_, r), lab, pos) in enumerate(zip(df.iterrows(), labels, text_pos)):
        ax.annotate(lab, xy=(r["length_km"], r["c_proxy_m"]), xytext=pos,
                    fontsize=7.8, va="top", ha="left", color=colors[i],
                    arrowprops=dict(arrowstyle="-", color=colors[i], lw=0.8,
                                    shrinkA=2, shrinkB=5))

    ax.text(7.18, 3000, "解 2 → 解 3：距离 +7.09%，C −19.0%（相对解 2）",
            fontsize=7.2, color="#666666")

    ax.set_xlabel("路线长度 (km)")
    ax.set_ylabel("累计暴露 C（代理·米）")
    ax.set_title("核心 OD 的 3 个解：等长 tie-break 与真绕行", fontsize=9)
    ax.set_xlim(6.98, 7.62)
    ax.set_ylim(2490, 4000)
    ax.grid(alpha=0.15, lw=0.4)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_pareto.png", bbox_inches="tight")
    fig.savefig(OUT / "fig4_pareto.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    cfg = load_config()
    grid = build_grid(cfg)
    fig_airspace(cfg, grid)
    fig_population(cfg, grid)
    fig_routes(cfg, grid)
    fig_pareto()
    for p in sorted(OUT.glob("*.png")):
        print(f"图：{p}")


if __name__ == "__main__":
    main()
