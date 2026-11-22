"""网格构建与坐标转换的单元测试（Day 9：网格类核心逻辑）。"""
from __future__ import annotations

import numpy as np
import pytest

from src.config import load_config
from src.grid import aoi_mask, build_grid, cell_of_point, edges_to_lonlat, point_to_metric


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def grid(cfg):
    return build_grid(cfg)


def test_grid_shape_matches_cell_size(cfg, grid):
    assert grid.cell_m == 200.0
    assert grid.shape == (98, 128)
    assert grid.cols == len(grid.xs) == len(grid.x_edges) - 1
    assert grid.rows == len(grid.ys) == len(grid.y_edges) - 1


def test_rows_run_north_to_south(grid):
    assert np.all(np.diff(grid.ys) < 0)
    assert np.all(np.diff(grid.y_edges) < 0)
    assert np.all(np.diff(grid.xs) > 0)


def test_transform_matches_grid_origin(grid):
    t = grid.transform
    assert t.a == pytest.approx(grid.cell_m)
    assert t.e == pytest.approx(-grid.cell_m)
    assert t.c == pytest.approx(grid.x0)
    assert t.f == pytest.approx(grid.y1)


def test_bounds_metric_cover_aoi(cfg, grid):
    minx, miny, maxx, maxy = grid.bounds_metric()
    assert maxx - minx == pytest.approx(grid.cols * grid.cell_m)
    assert maxy - miny == pytest.approx(grid.rows * grid.cell_m)
    # bbox 的 UTM 范围应被网格覆盖（允许向外取整不到 1 格）
    (wx, sy), (ex, ny) = (point_to_metric(cfg, *cfg.bbox[:2]),
                          point_to_metric(cfg, *cfg.bbox[2:]))
    assert minx <= wx + 1e-6 and miny <= sy + 1e-6
    assert maxx >= ex - 1e-6 and maxy >= ny - 1e-6


def test_cell_of_point_roundtrips_center(cfg, grid):
    r, c = 40, 60
    # 取该格中心反算经纬度，再定位应回到同一格
    lon, lat = edges_to_lonlat(grid, cfg.crs_input)
    lon_c = 0.25 * (lon[r, c] + lon[r, c + 1] + lon[r + 1, c] + lon[r + 1, c + 1])
    lat_c = 0.25 * (lat[r, c] + lat[r, c + 1] + lat[r + 1, c] + lat[r + 1, c + 1])
    assert cell_of_point(cfg, grid, lon_c, lat_c) == (r, c)


def test_cell_of_point_clips_outside_bbox(cfg, grid):
    assert cell_of_point(cfg, grid, 113.0, 22.0) == (grid.rows - 1, 0)
    assert cell_of_point(cfg, grid, 115.0, 23.0) == (0, grid.cols - 1)


def test_edges_to_lonlat_has_expected_shape(grid, cfg):
    lon, lat = edges_to_lonlat(grid, cfg.crs_input)
    assert lon.shape == (grid.rows + 1, grid.cols + 1)
    assert lat.shape == lon.shape
    # 西边界经度应小于东边界，南边界纬度应小于北边界
    assert np.nanmin(lon) < np.nanmax(lon)
    assert np.nanmin(lat) < np.nanmax(lat)


def test_aoi_mask_matches_bbox_after_outward_snap(cfg, grid):
    mask = aoi_mask(cfg, grid)
    assert mask.shape == grid.shape
    minx, miny, maxx, maxy = cfg.bbox
    lon, lat = edges_to_lonlat(grid, cfg.crs_input)
    # 网格只向外扩不到 1 格，AOI 内应占绝大多数
    assert mask.mean() > 0.85
    assert mask[50, 64]  # AOI 中部
