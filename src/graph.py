"""把可通行网格转成 8 邻接图。

节点 = (row, col)；边权 = 平面长度（米）。对角边只在两个正交邻格都可通行时
才加入（与 ``mask.neighbors`` 同一规则），避免斜边切过硬禁飞区角点。
"""
from __future__ import annotations

import networkx as nx
import numpy as np

from .grid import Grid
from .mask import neighbors


def build_graph(grid: Grid, blocked: np.ndarray, connectivity: int = 8) -> nx.Graph:
    """构建无向图。节点只包含可通行格，边带 ``length_m`` 属性。"""
    free = ~blocked
    rows, cols = np.nonzero(free)
    graph = nx.Graph()
    graph.add_nodes_from((int(r), int(c)) for r, c in zip(rows, cols))

    for r, c in graph.nodes:
        for nr, nc in neighbors(grid, blocked, r, c, connectivity):
            if graph.has_edge((r, c), (nr, nc)):
                continue
            dx = float(grid.xs[nc] - grid.xs[c])
            dy = float(grid.ys[nr] - grid.ys[r])
            graph.add_edge((r, c), (nr, nc), length_m=float(np.hypot(dx, dy)))
    return graph


def graph_stats(graph: nx.Graph) -> dict[str, float]:
    """节点/边数与连通分量，写日志用。"""
    if graph.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "components": 0, "largest_component": 0}
    components = list(nx.connected_components(graph))
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "components": len(components),
        "largest_component": max(len(c) for c in components),
    }
