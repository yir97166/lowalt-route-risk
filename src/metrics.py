"""指标定义与单位（正式定义见 ``docs/indicator_definition.md``）。

记号
----
``e_ij``
    暴露代理面，无量纲，取值 [0, 1]：

    e_ij = clip(pop_ij / p95, 0, 1) × severity × (1 − shelter) × alt_factor(h)

``l_e``
    边 e 的平面长度，单位 m。

``ē_e``
    边两端格暴露的算术平均 ``(e_a + e_b) / 2``，无量纲。

``C(R)``
    等效暴露长度（equivalent exposure length）：

    C(R) = Σ_e l_e · ē_e

    单位是「代理·米」(proxy·m)：量纲仍是长度，但物理含义是
    「假设以暴露强度 1.0 飞完这段路，相当于飞了多少米」。
    因为 ē ≤ 1，恒有 C ≤ L；C 只能在同一套人口/遮蔽/高度假设内做**相对**比较，
    不能与航路长度直接比大小，也不是伤亡人数、失效概率或 SORA 地面风险等级。

``E(R)``
    平均暴露强度 ``C / L``，无量纲，取值 [0, 1]。跨网格分辨率可比。

``ρ̄(R)``
    沿路人口密度 ``Σ_e l_e · ρ_e / L``，单位 人/km²。跨网格分辨率可比。

注意
----
旧的 ``route_exposure_m`` 与新定义的 ``C`` 数值相同，只是列名/单位表述不清
（曾被写成「累计暴露 2,840.3 m」，正确写法是「C = 2,840.3 代理·米」）。
新代码请用本模块的 :func:`route_metrics`，它同时给出 C、E、ρ̄。
"""
from __future__ import annotations

from typing import Iterable

import numpy as np


def edge_mean_exposure(
    a: tuple[int, int], b: tuple[int, int], exposure: np.ndarray
) -> float:
    """边的暴露强度 ē_e（两端格暴露均值，无量纲）。"""
    return 0.5 * (float(exposure[a]) + float(exposure[b]))


def cumulative_exposure(
    graph, cells: Iterable[tuple[int, int]], exposure: np.ndarray
) -> float:
    """等效暴露长度 C(R)，单位「代理·米」(proxy·m)。"""
    cells = list(cells)
    total = 0.0
    for a, b in zip(cells, cells[1:]):
        total += float(graph.edges[a, b]["length_m"]) * edge_mean_exposure(a, b, exposure)
    return total


def route_metrics(
    graph,
    cells: Iterable[tuple[int, int]],
    exposure: np.ndarray,
    *,
    pop: np.ndarray | None = None,
    cell_m: float | None = None,
) -> dict[str, float]:
    """一条路线的四项指标：L（m）、C（代理·米）、E（无量纲）、ρ̄（人/km²）。

    ``pop`` 给每格人口数（不是密度），``cell_m`` 为格边长；
    两者都给时才计算 ρ̄，否则 ``density_km2`` 返回 ``nan``。
    """
    cells = list(cells)
    length_m = 0.0
    c_proxy_m = 0.0
    weighted_density = 0.0
    area_m2 = float(cell_m) ** 2 if cell_m else None
    for a, b in zip(cells, cells[1:]):
        seg = float(graph.edges[a, b]["length_m"])
        length_m += seg
        c_proxy_m += seg * edge_mean_exposure(a, b, exposure)
        if pop is not None and area_m2:
            dens = 0.5 * (float(pop[a]) + float(pop[b])) / area_m2
            weighted_density += dens * seg
    intensity = c_proxy_m / length_m if length_m > 0 else float("nan")
    density_km2 = (
        (weighted_density / length_m) * 1e6
        if length_m > 0 and pop is not None and area_m2
        else float("nan")
    )
    return {
        "length_m": length_m,
        "c_proxy_m": c_proxy_m,
        "intensity": intensity,
        "density_km2": density_km2,
    }
