r"""核对人口栅格（可以先拿合成数据自测，再换真实 WorldPop）。

用法：
    python scripts/check_worldpop.py                    # 读 configs/aoi.yaml 里配置的 tif（优先真实数据）
    python scripts/check_worldpop.py --tif data/processed/synthetic_population.tif

只读，不写任何文件；输出：栅格范围、网格聚合后的总人口、p95、最大值、非零格数，
以及核心 OD 的 λ=0 / λ=1 路线长度与累计暴露 C，用于和合成数据对比。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402
from src.data import aggregate_population_to_grid, pick_population_path  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.mask import blocked_mask, feasible_od  # noqa: E402
from src.risk import exposure_surface, normalize_population  # noqa: E402
from src.router import plan_route_weighted, route_exposure_m  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="只读核对人口栅格与核心 OD 指标")
    parser.add_argument("--tif", default=None, help="人口 tif；默认按 configs/aoi.yaml 选择")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    cfg = load_config(Path(args.config) if args.config else None)
    tif = Path(args.tif) if args.tif else pick_population_path(cfg)
    grid = build_grid(cfg)
    pop = aggregate_population_to_grid(tif, grid, cfg)
    pop_norm, p95 = normalize_population(pop, cfg.risk.population_percentile)
    exposure = exposure_surface(pop_norm, cfg.risk)

    print(f"tif      : {tif}")
    print(f"grid     : {grid.rows} x {grid.cols}  cell={grid.cell_m:.0f} m")
    print(f"total    : {pop.sum():,.1f}")
    print(f"p95      : {p95:,.4f}")
    print(f"max cell : {pop.max():,.1f}")
    print(f"nonzero  : {int((pop > 0).sum()):,} / {pop.size:,}")
    print(f"exposure : max={exposure.max():.3f}")

    blocked = blocked_mask(cfg, grid)
    print(f"blocked  : {int(blocked.sum()):,} ({blocked.mean() * 100:.2f}%)")

    core = next(od for od in cfg.od_pairs if od.role == "core")
    o, d, ok = feasible_od(cfg, grid, blocked, core)
    if not ok:
        print("core OD  : 不可达（端点落在硬禁飞区）")
        return 0
    graph = build_graph(grid, blocked)
    for lam in (0.0, 1.0):
        route = plan_route_weighted(graph, grid, (o.row, o.col), (d.row, d.col), exposure, lam)
        if route is None:
            print(f"lambda={lam:<4}: 不可达")
            continue
        c = route_exposure_m(graph, route.cells, exposure)
        print(f"lambda={lam:<4}: length={route.length_m / 1000:.3f} km  C={c:,.1f}  detour={route.detour_ratio:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
