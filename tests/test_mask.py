"""禁飞硬掩膜、切角规则、吸附与几何验证的单元测试。"""
from __future__ import annotations

import numpy as np
import pytest

from src.config import load_config
from src.grid import Grid, build_grid, cell_of_point
from src.mask import (
    blocked_mask,
    nearest_free_cell,
    neighbors,
    validate_path,
    zone_geometries,
)


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def grid(cfg):
    return build_grid(cfg)


def tiny_grid() -> Grid:
    rows = cols = 3
    cell = 200.0
    y1 = rows * cell
    xs = (np.arange(cols) + 0.5) * cell
    ys = y1 - (np.arange(rows) + 0.5) * cell
    return Grid(
        rows=rows,
        cols=cols,
        cell_m=cell,
        crs="EPSG:32649",
        x0=0.0,
        y1=y1,
        xs=xs,
        ys=ys,
        x_edges=np.arange(cols + 1) * cell,
        y_edges=y1 - np.arange(rows + 1) * cell,
    )


def test_zone_geometries_are_metric(cfg):
    zones = zone_geometries(cfg)
    assert len(zones) == len(cfg.no_fly)
    # 机场圆半径 5 km，米制坐标下面积应约 π·5000²
    _, circle = zones[0]
    assert circle.area == pytest.approx(np.pi * 5000**2, rel=0.01)


def test_blocked_mask_shape_and_some_cells(cfg, grid):
    blocked = blocked_mask(cfg, grid)
    assert blocked.shape == grid.shape
    assert blocked.dtype == bool
    # 两个多边形禁飞区都在 AOI 内，必然有不可通行格
    assert blocked.sum() > 0
    # 西南角远离所有禁飞区，应可通行
    assert not blocked[-1, 0]


def test_polygon_zone_center_is_blocked(cfg, grid):
    blocked = blocked_mask(cfg, grid)
    r, c = cell_of_point(cfg, grid, 113.99, 22.61)  # 梧桐山示意多边形中心
    assert blocked[r, c]
    r2, c2 = cell_of_point(cfg, grid, 113.90, 22.52)
    assert not blocked[r2, c2]


def test_diagonal_corner_cutting_is_rejected():
    g = tiny_grid()
    blocked = np.zeros(g.shape, dtype=bool)
    # 先确认没有阻挡时，(0,0) 可以斜走到 (1,1)
    assert (1, 1) in neighbors(g, blocked, 0, 0, connectivity=8)
    # 挡住 (0,1) 后，斜边会切过它的角，必须禁止
    blocked[0, 1] = True
    assert (1, 1) not in neighbors(g, blocked, 0, 0, connectivity=8)
    # 四邻接本来就不含对角，行为不变
    assert (1, 1) not in neighbors(g, blocked, 0, 0, connectivity=4)


def test_nearest_free_snap_inside_zone(cfg, grid):
    blocked = blocked_mask(cfg, grid)
    r, c = cell_of_point(cfg, grid, 113.99, 22.61)
    assert blocked[r, c]
    snap = nearest_free_cell(cfg, grid, blocked, 113.99, 22.61)
    assert not blocked[snap.row, snap.col]
    assert snap.offset_m > 0
    assert (snap.row, snap.col) != (r, c)


def test_validate_path_detects_zone_crossing(cfg, grid):
    blocked = blocked_mask(cfg, grid)
    # 沿同一行横穿梧桐山多边形（用禁飞格序列，不传 blocked，验证独立几何检查）
    r, c0 = cell_of_point(cfg, grid, 113.97, 22.61)
    _, c1 = cell_of_point(cfg, grid, 114.01, 22.61)
    cells = [(r, c) for c in range(c0, c1 + 1)]
    result = validate_path(cells, grid, cfg)
    assert result.crossings > 0
    assert not result.ok


def test_validate_path_flags_blocked_cell(cfg, grid):
    blocked = blocked_mask(cfg, grid)
    r, c = cell_of_point(cfg, grid, 113.99, 22.61)
    cells = [(r, c - 1), (r, c), (r, c + 1)]
    result = validate_path(cells, grid, cfg, blocked=blocked)
    assert any("禁飞格" in issue for issue in result.issues)


def test_validate_path_ok_for_short_free_segment(cfg, grid):
    blocked = blocked_mask(cfg, grid)
    r, c = cell_of_point(cfg, grid, 113.90, 22.52)
    assert not blocked[r, c] and not blocked[r, c + 1]
    result = validate_path([(r, c), (r, c + 1)], grid, cfg, blocked=blocked)
    assert result.ok
    assert result.crossings == 0
    assert result.length_m == pytest.approx(grid.cell_m)
