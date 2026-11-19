"""路由：Dijkstra 最短路与路线指标。

Day 3 只用边的 ``length_m`` 权重（λ = 0 的 baseline）；Day 4 起权重改为
``length_m × (1 + λ × exposure)``，接口保持不变。
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from .grid import Grid


@dataclass(frozen=True)
class Route:
    """一条格心序列及其指标（长度单位 m）。"""

    cells: tuple[tuple[int, int], ...]
    length_m: float
    straight_m: float

    @property
    def detour_ratio(self) -> float:
        return self.length_m / self.straight_m if self.straight_m > 0 else float("nan")


def shortest_path(
    graph: nx.Graph,
    start: tuple[int, int],
    goal: tuple[int, int],
    weight: str = "length_m",
) -> list[tuple[int, int]]:
    """Dijkstra 最短路径；不可达时抛 ``networkx.NetworkXNoPath``。"""
    if start not in graph or goal not in graph:
        raise nx.NodeNotFound(f"起点或终点不在图中：{start} / {goal}")
    return list(nx.dijkstra_path(graph, start, goal, weight=weight))


def path_length(graph: nx.Graph, cells: list[tuple[int, int]]) -> float:
    """按边的 ``length_m`` 求和；缺边视为数据错误。"""
    total = 0.0
    for a, b in zip(cells, cells[1:]):
        total += float(graph.edges[a, b]["length_m"])
    return total


def plan_route(
    graph: nx.Graph,
    grid: Grid,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> Route:
    """算最短路并给出直线距离/绕行率，单位均为米。"""
    cells = shortest_path(graph, start, goal)
    length = path_length(graph, cells)
    (r0, c0), (r1, c1) = cells[0], cells[-1]
    straight = float(np.hypot(grid.xs[c1] - grid.xs[c0], grid.ys[r1] - grid.ys[r0]))
    return Route(cells=tuple(cells), length_m=length, straight_m=straight)
