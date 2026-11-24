"""绘图：Day 1 的人口热力图（含起降点与示意禁飞区）。"""
from __future__ import annotations

import os
from pathlib import Path

# OneDrive / 非 ASCII 用户名下 matplotlib 默认缓存目录可能不可写，固定到项目内。
_MPL_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
if not os.environ.get("MPLCONFIGDIR"):
    os.environ["MPLCONFIGDIR"] = str(_MPL_CACHE)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MplPolygon
from matplotlib.ticker import FuncFormatter
from pyproj import Transformer

from .config import Config
from .grid import Grid, edges_to_lonlat
from .mask import zone_geometries

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _circle_lonlat(cfg: Config, center: tuple[float, float], radius_m: float) -> np.ndarray:
    to_metric = Transformer.from_crs(cfg.crs_input, cfg.crs_metric, always_xy=True)
    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)
    cx, cy = to_metric.transform(center[0], center[1])
    theta = np.linspace(0.0, 2.0 * np.pi, 180)
    lons, lats = to_geo.transform(cx + radius_m * np.cos(theta), cy + radius_m * np.sin(theta))
    return np.column_stack([lons, lats])


def plot_route(
    cfg: Config,
    grid: Grid,
    pop: np.ndarray,
    cells: list[tuple[int, int]],
    out_path: str | Path,
    source_label: str = "合成数据",
) -> Path:
    """人口底图上画一条路线（格心序列），标起终点。"""
    lon_e, lat_e = edges_to_lonlat(grid, cfg.crs_input)
    shown = np.log10(pop + 1.0)
    minx, miny, maxx, maxy = cfg.bbox
    lat_mid = float(np.mean(lat_e))

    fig, ax = plt.subplots(figsize=(11, 8.2), dpi=300)
    mesh = ax.pcolormesh(lon_e, lat_e, shown, cmap="magma", shading="flat")
    cbar = fig.colorbar(mesh, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label("人口（每 200 m 格，log10 显示）", fontsize=10)
    cbar.ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{10 ** v:,.0f}" if v >= 0 else "")
    )
    mesh.set_clip_path(MplPolygon(
        [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)],
        closed=True, transform=ax.transData))
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)

    def _ring(g) -> np.ndarray:
        xs, ys = np.asarray(g.exterior.coords).T
        lons, lats = to_geo.transform(xs, ys)
        return np.column_stack([lons, lats])

    for z, (_, geom) in zip(cfg.no_fly, zone_geometries(cfg)):
        ring = _ring(geom)
        if z.hard:
            ax.add_patch(MplPolygon(ring, closed=True, facecolor="white", alpha=0.25,
                                    edgecolor="white", lw=1.6, ls="--", zorder=3))
        else:
            ax.plot(ring[:, 0], ring[:, 1], color="#ff4d4d", lw=1.5, ls="--", zorder=3)

    xs = [float(grid.xs[c]) for _, c in cells]
    ys = [float(grid.ys[r]) for r, _ in cells]
    lons, lats = to_geo.transform(xs, ys)
    ax.plot(lons, lats, color="black", lw=4.2, solid_capstyle="round", zorder=5)
    ax.plot(lons, lats, color="#00e5ff", lw=2.2, solid_capstyle="round", zorder=6)
    ax.scatter(lons[0], lats[0], marker="^", s=190, c="#20d020", edgecolor="black", zorder=7)
    ax.scatter(lons[-1], lats[-1], marker="v", s=190, c="#2080ff", edgecolor="black", zorder=7)

    handles = [
        Line2D([], [], color="#00e5ff", lw=2.5, label="最短可行路线（λ = 0）"),
        Line2D([], [], marker="^", ls="", markersize=11, markerfacecolor="#20d020",
               markeredgecolor="black", label="起点 O（北站）"),
        Line2D([], [], marker="v", ls="", markersize=11, markerfacecolor="#2080ff",
               markeredgecolor="black", label="终点 D（深圳湾）"),
        Patch(facecolor="white", alpha=0.5, edgecolor="white", ls="--",
              label="硬禁飞区（示意）"),
        Line2D([], [], color="#ff4d4d", lw=1.5, ls="--",
               label="机场净空保护区（硬禁飞）"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.9)
    ax.set_title(
        f"最短可行路线 baseline · 200 m 网格（{source_label}）\n"
        f"AOI {grid.cols}×{grid.rows} 格 · 8 邻接 Dijkstra",
        fontsize=13,
    )
    ax.set_xlabel("经度 (°E)")
    ax.set_ylabel("纬度 (°N)")
    ax.set_aspect(1.0 / max(np.cos(np.radians(lat_mid)), 1e-6))
    ax.text(0.99, 0.01, "数据仅用于方法演示，不构成运行依据",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="white",
            bbox=dict(boxstyle="round", fc="black", alpha=0.55, ec="none"))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_route_compare(
    cfg: Config,
    grid: Grid,
    pop: np.ndarray,
    baseline_cells: list[tuple[int, int]],
    weighted_cells: list[tuple[int, int]],
    out_path: str | Path,
    lam: float,
    od_label: str,
    source_label: str = "合成数据",
) -> Path:
    """同一张人口底图上画 baseline 与暴露加权两条路线。"""
    lon_e, lat_e = edges_to_lonlat(grid, cfg.crs_input)
    shown = np.log10(pop + 1.0)
    minx, miny, maxx, maxy = cfg.bbox
    lat_mid = float(np.mean(lat_e))

    fig, ax = plt.subplots(figsize=(11, 8.2), dpi=300)
    mesh = ax.pcolormesh(lon_e, lat_e, shown, cmap="magma", shading="flat")
    cbar = fig.colorbar(mesh, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label("人口（每 200 m 格，log10 显示）", fontsize=10)
    cbar.ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{10 ** v:,.0f}" if v >= 0 else "")
    )
    mesh.set_clip_path(MplPolygon(
        [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)],
        closed=True, transform=ax.transData))
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)

    def _ring(g) -> np.ndarray:
        xs, ys = np.asarray(g.exterior.coords).T
        lons, lats = to_geo.transform(xs, ys)
        return np.column_stack([lons, lats])

    for z, (_, geom) in zip(cfg.no_fly, zone_geometries(cfg)):
        ring = _ring(geom)
        if z.hard:
            ax.add_patch(MplPolygon(ring, closed=True, facecolor="white", alpha=0.25,
                                    edgecolor="white", lw=1.6, ls="--", zorder=3))
        else:
            ax.plot(ring[:, 0], ring[:, 1], color="#ff4d4d", lw=1.5, ls="--", zorder=3)

    def _lonlat(cells):
        xs = [float(grid.xs[c]) for _, c in cells]
        ys = [float(grid.ys[r]) for r, _ in cells]
        return to_geo.transform(xs, ys)

    lons0, lats0 = _lonlat(baseline_cells)
    lons1, lats1 = _lonlat(weighted_cells)
    ax.plot(lons0, lats0, color="black", lw=4.0, solid_capstyle="round", zorder=5)
    ax.plot(lons0, lats0, color="#00e5ff", lw=2.0, solid_capstyle="round", zorder=6,
            label=f"baseline（λ=0）")
    ax.plot(lons1, lats1, color="black", lw=4.6, solid_capstyle="round", zorder=7)
    ax.plot(lons1, lats1, color="#ff3df0", lw=2.6, solid_capstyle="round", zorder=8,
            label=f"暴露加权（λ={lam:g}）")
    ax.scatter(lons0[0], lats0[0], marker="^", s=190, c="#20d020", edgecolor="black", zorder=9)
    ax.scatter(lons0[-1], lats0[-1], marker="v", s=190, c="#2080ff", edgecolor="black", zorder=9)

    handles = [
        Line2D([], [], color="#00e5ff", lw=2.5, label="baseline（λ=0）"),
        Line2D([], [], color="#ff3df0", lw=3.0, label=f"暴露加权（λ={lam:g}）"),
        Line2D([], [], marker="^", ls="", markersize=11, markerfacecolor="#20d020",
               markeredgecolor="black", label="起点 O"),
        Line2D([], [], marker="v", ls="", markersize=11, markerfacecolor="#2080ff",
               markeredgecolor="black", label="终点 D"),
        Patch(facecolor="white", alpha=0.5, edgecolor="white", ls="--",
              label="硬禁飞区（示意）"),
        Line2D([], [], color="#ff4d4d", lw=1.5, ls="--", label="机场净空保护区（硬禁飞）"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.9)
    ax.set_title(
        f"baseline vs 人口暴露加权 · {od_label}\n"
        f"200 m 网格（{source_label}）· 边权 = 长度 × (1 + λ × 暴露)",
        fontsize=13,
    )
    ax.set_xlabel("经度 (°E)")
    ax.set_ylabel("纬度 (°N)")
    ax.set_aspect(1.0 / max(np.cos(np.radians(lat_mid)), 1e-6))
    ax.text(0.99, 0.01, "数据仅用于方法演示，不构成运行依据",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="white",
            bbox=dict(boxstyle="round", fc="black", alpha=0.55, ec="none"))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_population_map(
    cfg: Config,
    grid: Grid,
    pop: np.ndarray,
    exposure: np.ndarray,
    out_path: str | Path,
    source_label: str,
    od_index: int = 0,
) -> Path:
    """画 200 m 网格人口热力图，标出起降点与示意禁飞区。"""
    lon_e, lat_e = edges_to_lonlat(grid, cfg.crs_input)
    p95 = np.percentile(pop[pop > 0], cfg.risk.population_percentile) if np.any(pop > 0) else 0.0
    shown = np.log10(pop + 1.0)
    lat_mid = float(np.mean(lat_e))

    fig, ax = plt.subplots(figsize=(11, 8.2), dpi=300)
    mesh = ax.pcolormesh(lon_e, lat_e, shown, cmap="magma", shading="flat")
    cbar = fig.colorbar(mesh, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label("人口（每 200 m 格，log10 显示）", fontsize=10)
    cbar.ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{10 ** v:,.0f}" if v >= 0 else "")
    )

    minx, miny, maxx, maxy = cfg.bbox
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    # 网格按 200 m 外扩到 bbox 之外；显示时裁回 AOI，避免阶梯状边缘。
    mesh.set_clip_path(MplPolygon(
        [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)],
        closed=True, transform=ax.transData))

    zone_handles = []
    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)

    def _ring(g) -> np.ndarray:
        xs, ys = np.asarray(g.exterior.coords).T
        lons, lats = to_geo.transform(xs, ys)
        return np.column_stack([lons, lats])

    for z, (_, geom) in zip(cfg.no_fly, zone_geometries(cfg)):
        ring = _ring(geom)
        if z.hard:
            ax.add_patch(MplPolygon(ring, closed=True, facecolor="white", alpha=0.25,
                                    edgecolor="white", lw=1.6, ls="--"))
        else:
            ax.plot(ring[:, 0], ring[:, 1], color="#ff4d4d", lw=1.8, ls="--")
    zone_handles.append(Patch(facecolor="white", alpha=0.5, edgecolor="white", ls="--",
                              label="硬禁飞区（示意）：两个敏感多边形"))
    zone_handles.append(Line2D([], [], color="#ff4d4d", lw=1.8, ls="--",
                               label="机场净空保护区（官方尺寸，硬禁飞）"))

    od = cfg.od_pairs[od_index]
    ax.scatter(*od.origin, marker="^", s=170, c="#20d020", edgecolor="black", zorder=6)
    ax.scatter(*od.destination, marker="v", s=170, c="#2080ff", edgecolor="black", zorder=6)
    handles = [
        Line2D([], [], marker="^", ls="", markersize=11, markerfacecolor="#20d020",
               markeredgecolor="black", label="起点 O（北站）"),
        Line2D([], [], marker="v", ls="", markersize=11, markerfacecolor="#2080ff",
               markeredgecolor="black", label="终点 D（深圳湾）"),
        *zone_handles,
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.9)

    ax.set_title(
        f"深圳中西部人口热力图 · 200 m 网格（{source_label}）\n"
        f"AOI {grid.cols}×{grid.rows} 格 · 高度 60 m 人口暴露代理 · 禁飞区 illustrative only",
        fontsize=13,
    )
    ax.set_xlabel("经度 (°E)")
    ax.set_ylabel("纬度 (°N)")
    ax.set_aspect(1.0 / max(np.cos(np.radians(lat_mid)), 1e-6))
    ax.text(0.99, 0.01, "数据仅用于方法演示，非官方禁飞区，不构成运行依据",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="white",
            bbox=dict(boxstyle="round", fc="black", alpha=0.55, ec="none"))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

    print(f"p95(非零人口)={p95:.2f} · 暴露代理 max={exposure.max():.3f} · 非零格={int((pop > 0).sum())}")
    return out_path
