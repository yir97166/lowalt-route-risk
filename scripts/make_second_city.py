"""第二城市案例：广州东站—广州南站，检验阈值/机制是否稳定。

用法：python scripts/make_second_city.py [configs/aoi_guangzhou.yaml]
输出：results/second_city_pareto.csv、results/second_city_summary.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import load_config  # noqa: E402
from src.data import load_grid_arrays  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.grid import build_grid  # noqa: E402
from src.mask import blocked_mask, feasible_od  # noqa: E402
from src.router import plan_route, plan_route_weighted, route_exposure_m  # noqa: E402


def solve_od(cfg, grid, pop, exposure, blocked, graph, od) -> tuple[pd.DataFrame, dict]:
    origin, dest, _ = feasible_od(cfg, grid, blocked, od)
    s, g = (origin.row, origin.col), (dest.row, dest.col)
    base = plan_route(graph, grid, s, g)
    base_length = base.length_m
    rows = []
    lam = 0.0
    while lam <= 2.0 + 1e-9:
        route = plan_route_weighted(graph, grid, s, g, exposure, lam) if lam > 0 else base
        rows.append({"od": od.name, "lambda": round(lam, 4),
                     "length_km": route.length_m / 1000.0,
                     "c_proxy_m": route_exposure_m(graph, route.cells, exposure),
                     "detour": route.length_m / base_length})
        lam += 0.025
    df = pd.DataFrame(rows)
    df["key"] = list(zip(df["length_km"].round(6), df["c_proxy_m"].round(3)))
    first = df.groupby("key", sort=False)["lambda"].min().reset_index()
    last = df.groupby("key", sort=False)["lambda"].max().reset_index()
    uniq = first.merge(last, on="key", suffixes=("_first", "_last"))
    uniq[["length_km", "c_proxy_m"]] = pd.DataFrame(uniq["key"].tolist(), index=uniq.index)
    uniq["length_km"] = uniq["length_km"].round(3)
    uniq["c_proxy_m"] = uniq["c_proxy_m"].round(3)
    uniq["detour"] = uniq["length_km"] / round(base_length / 1000.0, 3)
    uniq["c_drop_pct"] = (uniq["c_proxy_m"] / uniq["c_proxy_m"].iloc[0] - 1.0) * 100.0
    uniq = uniq.drop(columns=["key"]).sort_values("lambda_first").reset_index(drop=True)
    return uniq, {"od": od.name, "base_length_km": base_length / 1000.0,
                  "origin_density": float(pop[s]), "dest_density": float(pop[g])}


def main() -> int:
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "configs" / "aoi_guangzhou.yaml"
    cfg = load_config(cfg_path)
    grid = build_grid(cfg)
    pop, exposure = load_grid_arrays(cfg, grid)
    blocked = blocked_mask(cfg, grid)
    graph = build_graph(grid, blocked)

    parts, meta = [], []
    for od in cfg.od_pairs:
        try:
            uniq, info = solve_od(cfg, grid, pop, exposure, blocked, graph, od)
        except Exception as exc:  # noqa: BLE001
            print(f"{od.name}: 不可达/失败 {type(exc).__name__}")
            continue
        parts.append(uniq)
        meta.append(info)
        print(f"{od.name}: base {info['base_length_km']:.3f} km, {len(uniq)} 个解")
        print(uniq.round(4).to_string(index=False))

    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    df.to_csv(ROOT / "results" / "second_city_pareto.csv", index=False, encoding="utf-8")
    pd.DataFrame(meta).to_csv(ROOT / "results" / "second_city_summary.csv", index=False, encoding="utf-8")
    print(f"config={cfg_path.name} aoi={cfg.aoi_name} grid={grid.rows}x{grid.cols}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
