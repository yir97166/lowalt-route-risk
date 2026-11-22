"""配置层测试：OD 角色、批量 OD 可飞性、反例 OD 不可达。

对应 2026-11-22 的约定：4 组机场向 OD 作「净空区内不宜设起降点」反例，
另选 5 组走廊外 OD 做批量实验（见 docs/decisions.md 第 19 条）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.config import load_config
from src.grid import build_grid
from src.mask import blocked_mask, feasible_od

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def grid_and_mask(cfg):
    grid = build_grid(cfg)
    return grid, blocked_mask(cfg, grid)


def test_od_roles(cfg):
    roles = [od.role for od in cfg.od_pairs]
    assert roles.count("core") == 1
    assert roles.count("batch") == 4
    assert roles.count("infeasible_example") == 4
    assert len(roles) == 9


def test_od_coordinates_inside_bbox(cfg):
    minx, miny, maxx, maxy = cfg.bbox
    for od in cfg.od_pairs:
        for lon, lat in (od.origin, od.destination):
            assert minx <= lon <= maxx, f"{od.name} 经度越界: {lon}"
            assert miny <= lat <= maxy, f"{od.name} 纬度越界: {lat}"


def test_batch_ods_reachable(cfg, grid_and_mask):
    grid, blocked = grid_and_mask
    for od in cfg.od_pairs:
        if od.role == "infeasible_example":
            continue
        _, _, feasible = feasible_od(cfg, grid, blocked, od)
        assert feasible, f"{od.name} 应可飞"


def test_infeasible_examples_rejected(cfg, grid_and_mask):
    grid, blocked = grid_and_mask
    for od in cfg.od_pairs:
        if od.role != "infeasible_example":
            continue
        _, _, feasible = feasible_od(cfg, grid, blocked, od)
        assert not feasible, f"{od.name} 应判端点落在硬禁飞区"
