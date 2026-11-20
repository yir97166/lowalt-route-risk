"""Day 4：暴露加权路由的单元测试。"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from src.grid import Grid
from src.router import (
    edge_exposure,
    exposure_weight,
    plan_route_weighted,
    route_exposure_m,
)


def _line_grid(rows: int = 1, cols: int = 4, cell: float = 200.0) -> Grid:
    return Grid(
        rows=rows,
        cols=cols,
        cell_m=cell,
        crs="EPSG:32649",
        x0=0.0,
        y1=rows * cell,
        xs=np.arange(cols) * cell + cell / 2,
        ys=np.arange(rows) * cell + cell / 2,
        x_edges=np.arange(cols + 1) * cell,
        y_edges=np.arange(rows + 1) * cell,
    )


def _grid_graph(rows: int, cols: int) -> nx.Graph:
    g = nx.Graph()
    for r in range(rows):
        for c in range(cols):
            g.add_node((r, c))
            for dr, dc in ((0, 1), (1, 0)):
                rr, cc = r + dr, c + dc
                if rr < rows and cc < cols:
                    length = 200.0 if dr == 0 else 200.0
                    g.add_edge((r, c), (rr, cc), length_m=length)
    return g


def test_edge_exposure_is_mean_of_endpoints() -> None:
    exposure = np.array([[0.0, 0.4], [0.2, 0.6]])
    assert edge_exposure((0, 0), (0, 1), exposure) == pytest.approx(0.2)
    assert edge_exposure((1, 0), (1, 1), exposure) == pytest.approx(0.4)


def test_weight_increases_with_lambda() -> None:
    exposure = np.array([[1.0, 0.0], [0.0, 0.0]])
    w0 = exposure_weight(exposure, 0.0)
    w1 = exposure_weight(exposure, 1.0)
    assert w0((0, 0), (0, 1), {"length_m": 200.0}) == pytest.approx(200.0)
    assert w1((0, 0), (0, 1), {"length_m": 200.0}) == pytest.approx(300.0)


def test_lambda_weight_can_prefer_long_low_exposure_detour() -> None:
    # 2x3 网格；上排暴露 0，下排暴露 1。起点 (1,0)，终点 (1,2)。
    grid = _line_grid(rows=2, cols=3)
    graph = _grid_graph(2, 3)
    exposure = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    base = plan_route_weighted(graph, grid, (1, 0), (1, 2), exposure, lam=0.0)
    wtd = plan_route_weighted(graph, grid, (1, 0), (1, 2), exposure, lam=5.0)
    assert route_exposure_m(graph, base.cells, exposure) > 0
    # 绕行仍需上下各一次「跨界边」，各贡献 200×0.5；但比沿下排直走低得多。
    assert route_exposure_m(graph, wtd.cells, exposure) < route_exposure_m(
        graph, base.cells, exposure
    )
    assert wtd.length_m > base.length_m  # 绕到上排要多走


def test_lambda_zero_matches_length() -> None:
    grid = _line_grid()
    graph = _grid_graph(1, 4)
    exposure = np.full((1, 4), 0.3)
    route = plan_route_weighted(graph, grid, (0, 0), (0, 3), exposure, lam=0.0)
    assert route.length_m == pytest.approx(600.0)
    assert route_exposure_m(graph, route.cells, exposure) == pytest.approx(180.0)
