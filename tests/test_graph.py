"""建图、最短路与路线指标的单元测试。"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from src.config import load_config
from src.graph import build_graph
from src.grid import Grid, build_grid, cell_of_point
from src.mask import blocked_mask, validate_path
from src.router import plan_route, shortest_path


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
        rows=rows, cols=cols, cell_m=cell, crs="EPSG:32649", x0=0.0, y1=y1,
        xs=xs, ys=ys,
        x_edges=np.arange(cols + 1) * cell,
        y_edges=y1 - np.arange(rows + 1) * cell,
    )


def test_graph_nodes_are_free_cells(cfg, grid):
    blocked = blocked_mask(cfg, grid)
    graph = build_graph(grid, blocked)
    assert graph.number_of_nodes() == int((~blocked).sum())
    assert graph.number_of_nodes() > 0


def test_graph_has_no_edge_through_corner():
    g = tiny_grid()
    blocked = np.zeros(g.shape, dtype=bool)
    blocked[0, 1] = True  # 挡掉 (0,1)，(0,0)→(1,1) 的斜边会被切角规则拒绝
    graph = build_graph(g, blocked)
    assert not graph.has_edge((0, 0), (1, 1))
    # 但 (1,1) 与 (1,2) 之间仍应连通
    assert graph.has_edge((1, 1), (1, 2))


def test_shortest_path_prefers_straight_line():
    g = tiny_grid()
    blocked = np.zeros(g.shape, dtype=bool)
    graph = build_graph(g, blocked)
    cells = shortest_path(graph, (0, 0), (0, 2))
    assert cells == [(0, 0), (0, 1), (0, 2)]
    route = plan_route(graph, g, (0, 0), (0, 2))
    assert route.length_m == pytest.approx(400.0)
    assert route.straight_m == pytest.approx(400.0)
    assert route.detour_ratio == pytest.approx(1.0)


def test_core_od_route_is_connected_and_valid(cfg, grid):
    blocked = blocked_mask(cfg, grid)
    graph = build_graph(grid, blocked)
    od = cfg.od_pairs[0]
    r0, c0 = cell_of_point(cfg, grid, *od.origin)
    r1, c1 = cell_of_point(cfg, grid, *od.destination)
    # 起终点格本身必须可通行
    assert not blocked[r0, c0] and not blocked[r1, c1]
    route = plan_route(graph, grid, (r0, c0), (r1, c1))
    check = validate_path(list(route.cells), grid, cfg, blocked=blocked)
    assert check.ok, check.issues
    assert check.crossings == 0
    # 绕行率不应离谱（最短路在 8 邻接网格上通常 < 1.5）
    assert route.detour_ratio < 1.6


def test_unreachable_raises():
    graph = nx.Graph()
    graph.add_nodes_from([(0, 0), (1, 1)])
    with pytest.raises(nx.NetworkXNoPath):
        shortest_path(graph, (0, 0), (1, 1))
