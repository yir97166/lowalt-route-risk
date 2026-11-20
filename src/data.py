"""人口栅格读取与聚合。

Day 1 只做一件事：把 100 m 人口栅格聚合到 200 m 网格，得到每格人口。
优先真实 WorldPop；文件不存在时退回 data/processed/synthetic_population.tif。
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import Window, from_bounds

from .config import Config
from .grid import Grid


def pick_population_path(cfg: Config) -> Path:
    """优先真实数据，其次合成数据；都不存在就给出明确提示。"""
    candidates = [
        cfg.resolve(cfg.data[k]) for k in ("population_tif", "synthetic_tif") if cfg.data.get(k)
    ]
    for p in candidates:
        if p.is_file():
            return p
    pop = candidates[0] if candidates else cfg.root / "data" / "raw" / "worldpop" / "missing.tif"
    syn = candidates[1] if len(candidates) > 1 else cfg.root / "data" / "processed" / "synthetic_population.tif"
    raise FileNotFoundError(
        "找不到人口栅格。先运行：python scripts/make_synthetic_data.py\n"
        f"期望路径之一：{pop} 或 {syn}"
    )


def _source_pixel_area_m2(src: rasterio.DatasetReader, center_lat: float) -> float:
    """源像元面积（m²）。WorldPop 是 EPSG:4326，需按纬度换算。"""
    if src.crs is not None and src.crs.is_geographic:
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))
        return abs(src.transform.a) * m_per_deg_lon * abs(src.transform.e) * m_per_deg_lat
    return abs(src.transform.a * src.transform.e)


def aggregate_population_to_grid(tif_path: str | Path, grid: Grid, cfg: Config) -> np.ndarray:
    """把人口栅格重采样到网格，返回 (rows, cols) 的「每格人口数」。"""
    with rasterio.open(tif_path) as src:
        from pyproj import Transformer

        minx, miny, maxx, maxy = cfg.bbox
        t = Transformer.from_crs(cfg.crs_input, src.crs, always_xy=True)
        left, bottom = t.transform(minx, miny)
        right, top = t.transform(maxx, maxy)
        window = (
            from_bounds(left, bottom, right, top, transform=src.transform)
            .round_offsets()
            .round_lengths()
            .intersection(Window(0, 0, src.width, src.height))
        )
        if window.width <= 0 or window.height <= 0:
            raise ValueError(f"bbox 与栅格 {tif_path} 不相交")

        arr = src.read(1, window=window).astype("float64")
        nodata = src.nodata
        win_transform = src.window_transform(window)
        src_crs = src.crs
        pix_area = _source_pixel_area_m2(src, sum(cfg.bbox[1::2]) / 2)

    if nodata is not None:
        arr = np.where(arr == nodata, 0.0, arr)
    arr = np.where(np.isfinite(arr), arr, 0.0)
    arr = np.clip(arr, 0.0, None)

    dst = np.zeros(grid.shape, dtype="float64")
    reproject(
        source=arr,
        destination=dst,
        src_transform=win_transform,
        src_crs=src_crs,
        src_nodata=None,
        dst_transform=grid.transform,
        dst_crs=grid.crs,
        dst_nodata=0.0,
        resampling=Resampling.average,
    )
    # average 得到的是「每个源像元」的平均值；乘面积比换成每格总人口。
    dst *= (grid.cell_m**2) / pix_area
    return np.clip(dst, 0.0, None)


def load_grid_arrays(cfg, grid) -> tuple[np.ndarray, np.ndarray]:
    """从 Day 1 的网格表恢复 (population, exposure) 两个数组。

    列名兼容 ``exposure_cell``（v1.2 起）与旧列 ``risk_cell``。
    """
    import pandas as pd

    csv_path = cfg.resolve("data/processed/grid_population.csv")
    if not csv_path.exists():
        raise FileNotFoundError(
            f"缺少 {csv_path}；先跑 scripts/make_population_map.py"
        )
    df = pd.read_csv(csv_path)
    col = "exposure_cell" if "exposure_cell" in df.columns else "risk_cell"
    pop = np.zeros(grid.shape, dtype=float)
    expo = np.zeros(grid.shape, dtype=float)
    pop[df["row"].to_numpy(), df["col"].to_numpy()] = df["population"].to_numpy()
    expo[df["row"].to_numpy(), df["col"].to_numpy()] = df[col].to_numpy()
    return pop, expo
