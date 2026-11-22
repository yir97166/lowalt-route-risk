"""人口暴露代理面的单元测试（Day 9：风险类核心逻辑）。"""
from __future__ import annotations

import numpy as np
import pytest

from src.config import load_config
from src.risk import exposure_surface, normalize_population, risk_surface


def test_normalize_ignores_zero_cells():
    pop = np.array([[0.0, 0.0, 10.0, 20.0, 30.0, 40.0]])
    norm, p = normalize_population(pop, percentile=50)
    # 0 值不参与分位数；非零值 [10,20,30,40] 的 50 分位 = 25
    assert p == pytest.approx(25.0)
    assert norm[0, 0] == 0.0 and norm[0, 1] == 0.0
    assert norm.max() <= 1.0


def test_normalize_clips_at_one():
    pop = np.array([1.0, 2.0, 3.0, 100.0])
    norm, p = normalize_population(pop, percentile=75)
    assert p == pytest.approx(np.percentile([1, 2, 3, 100], 75))
    assert norm.max() == pytest.approx(1.0)
    assert np.all(norm >= 0.0)


def test_normalize_all_zero_is_safe():
    norm, p = normalize_population(np.zeros((2, 3)), percentile=95)
    assert p == 0.0
    assert np.all(norm == 0.0)


def test_normalize_handles_negative_values_safely():
    # 人口不应为负，但接口不应把负值算进分位数
    pop = np.array([-5.0, 0.0, 10.0, 20.0])
    norm, p = normalize_population(pop, percentile=50)
    assert p == pytest.approx(15.0)
    assert norm[0] == 0.0


def test_exposure_scales_linearly():
    cfg = load_config()
    pop_norm = np.array([[0.0, 0.5, 1.0]])
    e0 = exposure_surface(pop_norm, cfg.risk, altitude_m=60)
    e1 = exposure_surface(pop_norm * 0.5, cfg.risk, altitude_m=60)
    assert np.allclose(e1, e0 * 0.5, atol=1e-12)


def test_exposure_defaults_to_lowest_altitude():
    cfg = load_config()
    pop_norm = np.ones((2, 2))
    default = exposure_surface(pop_norm, cfg.risk)
    lowest = exposure_surface(pop_norm, cfg.risk, altitude_m=min(cfg.risk.altitude_factor))
    assert np.allclose(default, lowest)


def test_exposure_altitude_factor_is_applied():
    cfg = load_config()
    e60 = exposure_surface(np.ones(1), cfg.risk, altitude_m=60)
    e120 = exposure_surface(np.ones(1), cfg.risk, altitude_m=120)
    assert e120[0] == pytest.approx(e60[0] * cfg.risk.altitude_factor[120])


def test_exposure_upper_bound_follows_formula():
    cfg = load_config()
    e = exposure_surface(np.ones(3), cfg.risk, altitude_m=60)
    expected = cfg.risk.severity * (1.0 - cfg.risk.shelter) * cfg.risk.altitude_factor[60]
    assert e.max() == pytest.approx(expected)


def test_risk_surface_alias_is_exposure():
    cfg = load_config()
    pop_norm = np.array([[0.2, 0.8]])
    assert np.allclose(
        risk_surface(pop_norm, cfg.risk, altitude_m=60),
        exposure_surface(pop_norm, cfg.risk, altitude_m=60),
    )
