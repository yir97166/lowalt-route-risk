"""人口暴露代理面（population exposure proxy）。

exposure_cell = pop_norm × severity × (1 − shelter) × alt_factor
其中 pop_norm = min(pop / p95, 1)，p95 取 AOI 内非零格子的 95 分位。

注意：这里的值不是风险、伤亡概率或 SORA 地面风险等级，只是同一次实验内
用于比较不同路线的人口暴露相对强度。
"""
from __future__ import annotations

import numpy as np

from .config import RiskConfig


def normalize_population(pop: np.ndarray, percentile: float = 95.0) -> tuple[np.ndarray, float]:
    """按非零格子的分位数归一化到 [0, 1]。返回 (pop_norm, p_value)。"""
    values = np.asarray(pop, dtype="float64")
    nonzero = values[values > 0]
    p = float(np.percentile(nonzero, percentile)) if nonzero.size else 0.0
    if p <= 0:
        return np.zeros_like(values), 0.0
    return np.clip(values / p, 0.0, 1.0), p


def exposure_surface(
    pop_norm: np.ndarray,
    risk_cfg: RiskConfig,
    altitude_m: int | None = None,
) -> np.ndarray:
    """给定归一化人口，返回暴露代理面（0–1 量级）。altitude_m=None 表示 2D 最低层。

    altitude_factor 是无实证依据的情景参数，仅用于敏感性分析。
    """
    if altitude_m is None:
        altitudes = sorted(risk_cfg.altitude_factor) or [60]
        altitude_m = altitudes[0]
    alt_factor = float(risk_cfg.altitude_factor.get(altitude_m, 1.0))
    return (
        np.asarray(pop_norm, dtype="float64")
        * risk_cfg.severity
        * (1.0 - risk_cfg.shelter)
        * alt_factor
    )


# 兼容旧调用名；新代码请用 exposure_surface。
risk_surface = exposure_surface
