"""指标定义（C / E / ρ̄）的单元测试。

约束来自 docs/indicator_definition.md：
1. C = Σ l·ē，且因 ē ∈ [0,1] 必有 0 ≤ C ≤ L；
2. E = C / L，落在 [0, 1]；
3. 遮蔽/高度变动只缩放 e，不改变 L，因此 C 与 E 同步缩放；
4. 未给 pop 时 ρ̄ 为 nan，不留 0 冒充。
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np
import pytest

from src.metrics import cumulative_exposure, edge_mean_exposure, route_metrics

CELL = 200.0


def _grid_graph(rows: int, cols: int, cell: float = CELL) -> nx.Graph:
    g = nx.Graph()
    for r in range(rows):
        for c in range(cols):
            g.add_node((r, c))
            for dr, dc in ((0, 1), (1, 0)):
                rr, cc = r + dr, c + dc
                if rr < rows and cc < cols:
                    g.add_edge((r, c), (rr, cc), length_m=cell)
    return g


@pytest.fixture()
def exposure() -> np.ndarray:
    e = np.zeros((1, 5), dtype=float)
    e[0, 1] = 0.5
    e[0, 3] = 1.0
    return e


def test_edge_mean_exposure_is_average(exposure: np.ndarray) -> None:
    assert edge_mean_exposure((0, 0), (0, 1), exposure) == pytest.approx(0.25)
    assert edge_mean_exposure((0, 1), (0, 2), exposure) == pytest.approx(0.25)
    assert edge_mean_exposure((0, 2), (0, 3), exposure) == pytest.approx(0.5)


def test_cumulative_exposure_matches_hand_calc(exposure: np.ndarray) -> None:
    g = _grid_graph(1, 4)
    cells = [(0, 0), (0, 1), (0, 2), (0, 3)]
    # 200*(0.25 + 0.25 + 0.5) = 200
    assert cumulative_exposure(g, cells, exposure) == pytest.approx(200.0)


def test_c_is_never_greater_than_length(exposure: np.ndarray) -> None:
    g = _grid_graph(1, 5)
    cells = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]
    m = route_metrics(g, cells, exposure)
    assert 0.0 <= m["c_proxy_m"] <= m["length_m"]
    assert m["length_m"] == pytest.approx(4 * CELL)


def test_intensity_is_c_over_length(exposure: np.ndarray) -> None:
    g = _grid_graph(1, 5)
    cells = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]
    m = route_metrics(g, cells, exposure)
    assert m["intensity"] == pytest.approx(m["c_proxy_m"] / m["length_m"])
    assert 0.0 <= m["intensity"] <= 1.0


def test_density_uses_population_per_cell(exposure: np.ndarray) -> None:
    g = _grid_graph(1, 3)
    pop = np.array([[0.0, 100.0, 200.0]])
    cells = [(0, 0), (0, 1), (0, 2)]
    m = route_metrics(g, cells, exposure, pop=pop, cell_m=CELL)
    # 每格人口 / 格面积 = 密度；边长加权平均
    expected = ((0.0 + 100.0) / 2 / CELL**2 * CELL + (100.0 + 200.0) / 2 / CELL**2 * CELL) \
        / (2 * CELL) * 1e6
    assert m["density_km2"] == pytest.approx(expected)


def test_density_is_nan_without_population(exposure: np.ndarray) -> None:
    g = _grid_graph(1, 3)
    m = route_metrics(g, [(0, 0), (0, 1), (0, 2)], exposure)
    assert math.isnan(m["density_km2"])
