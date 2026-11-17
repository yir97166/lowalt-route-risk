"""bbox → 规则网格（UTM 米制）。Day 1 只需要 200 m 平面网格。

网格约定：
- 坐标用 crs_metric（默认 EPSG:32649, UTM 49N），单位米。
- row 0 在最北（与栅格数组一致），y 随 row 增大而减小。
- cell 中心坐标 xs[col], ys[row]；边界用 x_edges / y_edges。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pyproj import Transformer
from rasterio.transform import Affine

from .config import Config


@dataclass(frozen=True)
class Grid:
    rows: int
    cols: int
    cell_m: float
    crs: str
    x0: float  # 西边界（米）
    y1: float  # 北边界（米）
    xs: np.ndarray  # (cols,) 中心 easting
    ys: np.ndarray  # (rows,) 中心 northing，从北到南
    x_edges: np.ndarray  # (cols+1,)
    y_edges: np.ndarray  # (rows+1,)，从北到南

    @property
    def shape(self) -> tuple[int, int]:
        return self.rows, self.cols

    @property
    def transform(self) -> Affine:
        """栅格仿射变换（北向上），供 rasterio 使用。"""
        return Affine(self.cell_m, 0.0, self.x0, 0.0, -self.cell_m, self.y1)

    def bounds_metric(self) -> tuple[float, float, float, float]:
        return self.x0, self.y1 - self.rows * self.cell_m, self.x0 + self.cols * self.cell_m, self.y1


def build_grid(cfg: Config) -> Grid:
    """按 bbox + cell_size 生成网格；边界向外取整到整格。"""
    cell = float(cfg.grid.cell_size_m)
    to_metric = Transformer.from_crs(cfg.crs_input, cfg.crs_metric, always_xy=True)
    minx, miny, maxx, maxy = cfg.bbox
    (wx, sy), (ex, ny) = to_metric.transform(minx, miny), to_metric.transform(maxx, maxy)

    x0 = np.floor(min(wx, ex) / cell) * cell
    x1 = np.ceil(max(wx, ex) / cell) * cell
    y0 = np.floor(min(sy, ny) / cell) * cell
    y1 = np.ceil(max(sy, ny) / cell) * cell

    cols = int(round((x1 - x0) / cell))
    rows = int(round((y1 - y0) / cell))
    xs = x0 + (np.arange(cols) + 0.5) * cell
    ys = y1 - (np.arange(rows) + 0.5) * cell
    x_edges = x0 + np.arange(cols + 1) * cell
    y_edges = y1 - np.arange(rows + 1) * cell
    return Grid(rows, cols, cell, cfg.crs_metric, x0, y1, xs, ys, x_edges, y_edges)


def edges_to_lonlat(grid: Grid, crs_input: str) -> tuple[np.ndarray, np.ndarray]:
    """把网格边界顶点转回 WGS84，返回 (rows+1, cols+1) 的 lon/lat 数组。"""
    xx, yy = np.meshgrid(grid.x_edges, grid.y_edges)
    to_geo = Transformer.from_crs(grid.crs, crs_input, always_xy=True)
    lon, lat = to_geo.transform(xx, yy)
    return np.asarray(lon), np.asarray(lat)


def point_to_metric(cfg: Config, lon: float, lat: float) -> tuple[float, float]:
    t = Transformer.from_crs(cfg.crs_input, cfg.crs_metric, always_xy=True)
    x, y = t.transform(lon, lat)
    return float(x), float(y)


def cell_of_point(cfg: Config, grid: Grid, lon: float, lat: float) -> tuple[int, int]:
    """把经纬度点吸附到所在网格 (row, col)。"""
    x, y = point_to_metric(cfg, lon, lat)
    col = int(np.clip(np.floor((x - grid.x0) / grid.cell_m), 0, grid.cols - 1))
    row = int(np.clip(np.floor((grid.y1 - y) / grid.cell_m), 0, grid.rows - 1))
    return row, col


def aoi_mask(cfg: Config, grid: Grid) -> np.ndarray:
    """格心落在 AOI bbox 内的掩膜。网格为对齐 200 m 会略微外扩，外扩部分无数据。"""
    xx, yy = np.meshgrid(grid.xs, grid.ys)
    to_geo = Transformer.from_crs(grid.crs, cfg.crs_input, always_xy=True)
    lon, lat = to_geo.transform(xx, yy)
    minx, miny, maxx, maxy = cfg.bbox
    return (lon >= minx) & (lon <= maxx) & (lat >= miny) & (lat <= maxy)
