"""生成合成人口栅格，保证没有网络时也能跑通 pipeline。

用法：
    python scripts/make_synthetic_data.py

输出：
    data/processed/synthetic_population.tif

注意：合成数据只用于跑通流程/画图，不能用于真实结论。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import yaml

try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError as exc:  # pragma: no cover
    raise SystemExit("需要 rasterio：pip install rasterio") from exc

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "configs" / "aoi.yaml"


def gaussian(xx, yy, cx, cy, amp, sx, sy):
    return amp * np.exp(
        -(((xx - cx) ** 2) / (2 * sx**2) + ((yy - cy) ** 2) / (2 * sy**2))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="生成合成人口栅格（离线可跑）")
    parser.add_argument("--seed", type=int, default=None,
                        help="随机扰动种子；默认取 configs/aoi.yaml 的 data.synthetic_seed")
    args = parser.parse_args()

    cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    minx, miny, maxx, maxy = cfg["aoi"]["bbox"]
    out_path = ROOT / cfg["data"]["synthetic_tif"]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    res = 0.001  # 约 100 m，和真实 WorldPop 100 m 对齐
    cols = int(round((maxx - minx) / res))
    rows = int(round((maxy - miny) / res))
    xs = minx + (np.arange(cols) + 0.5) * res
    ys = maxy - (np.arange(rows) + 0.5) * res
    xx, yy = np.meshgrid(xs, ys)

    # 5 个高斯人口团：福田、南山、宝安中心、深圳北、罗湖
    # 幅度按「每 100 m 像元人数」标定，量级贴近深圳（峰值约 1,250 人/像元 ≈ 12.5 万人/km²）。
    centers = [
        (114.058, 22.543, 1_200, 0.012, 0.010),
        (113.930, 22.530, 900, 0.014, 0.012),
        (113.883, 22.555, 700, 0.012, 0.010),
        (114.029, 22.610, 600, 0.010, 0.009),
        (114.095, 22.548, 800, 0.009, 0.009),
    ]
    pop = np.full((rows, cols), 50.0, dtype=np.float64)  # 背景约 5,000 人/km²
    for cx, cy, amp, sx, sy in centers:
        pop += gaussian(xx, yy, cx, cy, amp, sx, sy)

    seed = args.seed if args.seed is not None else int(cfg["data"].get("synthetic_seed", 42))
    rng = np.random.default_rng(seed)
    pop *= 0.9 + 0.2 * rng.random(pop.shape)
    pop = np.clip(pop, 0, None).astype("float32")

    transform = from_origin(minx, maxy, res, res)
    with rasterio.open(
        out_path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        compress="lzw",
    ) as dst:
        dst.write(pop, 1)

    print(f"shape={pop.shape} min={pop.min():.1f} max={pop.max():.1f} mean={pop.mean():.1f}")
    print(f"seed={seed}")
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()
