"""Day 1 入口：人口栅格 → 200 m 网格 → 热力图 + 每格 CSV。

用法：
    python scripts/make_population_map.py            # 自动选真实/合成数据
    python scripts/make_population_map.py --synthetic

输出：
    figures/00_population.png
    data/processed/grid_population.csv  (row, col, lon, lat, population, pop_norm, risk_cell)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402
from src.data import aggregate_population_to_grid, pick_population_path  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.risk import normalize_population, risk_surface  # noqa: E402
from src.viz import plot_population_map  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 1：人口热力图")
    ap.add_argument("--config", default=None, help="配置文件路径")
    ap.add_argument("--synthetic", action="store_true", help="强制使用合成数据")
    ap.add_argument("--out", default="figures/00_population.png")
    ap.add_argument("--csv", default="data/processed/grid_population.csv")
    args = ap.parse_args()

    cfg = load_config(args.config)
    grid = build_grid(cfg)
    print(f"网格：{grid.rows} 行 × {grid.cols} 列，cell={grid.cell_m:g} m，CRS={grid.crs}")

    if args.synthetic:
        tif = cfg.resolve(cfg.data["synthetic_tif"])
        if not tif.exists():
            raise FileNotFoundError(f"合成数据不存在：{tif}\n先运行 python scripts/make_synthetic_data.py")
    else:
        tif = pick_population_path(cfg)
    source_label = "合成数据" if tif.name.startswith("synthetic") else "WorldPop 2020"
    print(f"人口栅格：{tif}（{source_label}）")

    pop = aggregate_population_to_grid(tif, grid, cfg)
    pop_norm, p95 = normalize_population(pop, cfg.risk.population_percentile)
    risk = risk_surface(pop_norm, cfg.risk, altitude_m=cfg.grid.altitudes_m[0])

    fig_path = plot_population_map(cfg, grid, pop, risk, cfg.resolve(args.out), source_label)

    from pyproj import Transformer

    to_geo = Transformer.from_crs(grid.crs, cfg.crs_input, always_xy=True)
    lon, lat = to_geo.transform(*np.meshgrid(grid.xs, grid.ys))
    rows, cols = np.indices(grid.shape)
    df = pd.DataFrame(
        {
            "row": rows.ravel(),
            "col": cols.ravel(),
            "lon": np.asarray(lon).ravel(),
            "lat": np.asarray(lat).ravel(),
            "population": pop.ravel(),
            "pop_norm": pop_norm.ravel(),
            "risk_cell": risk.ravel(),
        }
    )
    csv_path = cfg.resolve(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8")

    print(f"p95={p95:.2f}，总人口≈{pop.sum():,.0f}，最大格人口≈{pop.max():,.0f}")
    print(f"图：{fig_path}")
    print(f"表：{csv_path}（{len(df)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
