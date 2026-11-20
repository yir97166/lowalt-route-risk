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


def edge_exposure(a: tuple[int, int], b: tuple[int, int], exposure: np.ndarray) -> float:
    """边的暴露代理值：两端格心暴露的均值（无量纲，0–1）。"""
    return 0.5 * (float(exposure[a]) + float(exposure[b]))


def exposure_weight(exposure: np.ndarray, lam: float):
    """返回 networkx 可用的权重函数：length × (1 + λ × exposure)。"""
    def _weight(a, b, data):
        return float(data["length_m"]) * (1.0 + lam * edge_exposure(a, b, exposure))

    return _weight


def plan_route_weighted(
    graph: nx.Graph,
    grid: Grid,
    start: tuple[int, int],
    goal: tuple[int, int],
    exposure: np.ndarray,
    lam: float,
) -> Route:
    """暴露加权最短路；λ = 0 时与 ``plan_route`` 等价。"""
    if start not in graph or goal not in graph:
        raise nx.NodeNotFound(f"起点或终点不在图中：{start} / {goal}")
    cells = list(nx.dijkstra_path(graph, start, goal, weight=exposure_weight(exposure, lam)))
    length = path_length(graph, cells)
    (r0, c0), (r1, c1) = cells[0], cells[-1]
    straight = float(np.hypot(grid.xs[c1] - grid.xs[c0], grid.ys[r1] - grid.ys[r0]))
    return Route(cells=tuple(cells), length_m=length, straight_m=straight)


def route_exposure_m(
    graph: nx.Graph, cells: tuple[tuple[int, int], ...] | list[tuple[int, int]],
    exposure: np.ndarray,
) -> float:
    """累计暴露 = Σ(边长 × 边暴露)，单位 m（无量纲暴露 × 米）。"""
    total = 0.0
    for a, b in zip(cells, cells[1:]):
        total += float(graph.edges[a, b]["length_m"]) * edge_exposure(a, b, exposure)
    return total


def pareto_mask(lengths: np.ndarray, exposures: np.ndarray) -> np.ndarray:
    """返回非支配点掩码：长度更短且暴露不更高，或暴露更低且长度不更长。

    两个目标都是「越小越好」；完全相同的点只保留第一个。
    """
    n = len(lengths)
    keep = np.ones(n, dtype=bool)
    for i in range(n):
        if not keep[i]:
            continue
        for j in range(n):
            if i == j:
                continue
            no_worse = lengths[j] <= lengths[i] and exposures[j] <= exposures[i]
            strictly_better = lengths[j] < lengths[i] or exposures[j] < exposures[i]
            if no_worse and strictly_better:
                keep[i] = False
                break
            if keep[j] and lengths[j] == lengths[i] and exposures[j] == exposures[i] and j < i:
                keep[i] = False
                break
    return keep

