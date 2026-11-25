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
    """按配置或环境变量选择人口栅格；不再静默回退。

    mode=real（默认）：必须存在真实 WorldPop 栅格，否则报错并给出下载/切换方法。
    mode=synthetic：只允许合成栅格（用于没有真实数据的干净克隆）。
    可用环境变量 LOWALT_DATA_MODE 临时覆盖配置里的 data.mode。
    """
    import os

    mode = os.environ.get("LOWALT_DATA_MODE") or str(cfg.data.get("mode", "real"))
    mode = mode.strip().lower()

    pop = cfg.resolve(cfg.data["population_tif"]) if cfg.data.get("population_tif") else None
    syn = cfg.resolve(cfg.data["synthetic_tif"]) if cfg.data.get("synthetic_tif") else None

    if mode == "synthetic":
        if syn is not None and syn.is_file():
            return syn
        raise FileNotFoundError(
            "data.mode=synthetic，但找不到合成人口栅格。\n"
            "先运行：python scripts/make_synthetic_data.py\n"
            f"期望路径：{syn}"
        )

    if mode not in {"real", "synthetic"}:
        raise ValueError(f"未知 data.mode={mode!r}，只支持 real / synthetic")

    if pop is not None and pop.is_file():
        return pop

    raise FileNotFoundError(
        "找不到真实人口栅格，已停止，避免静默回退到合成数据覆盖结果。\n"
        f"期望路径：{pop}\n"
        "二选一：\n"
        "  1) 下载 WorldPop 2020 中国 100 m 约束版到该路径（约 625 MB，见 README『数据』一节）；\n"
        "  2) 没有真实数据时显式运行合成演示：\n"
        "     PowerShell: $env:LOWALT_DATA_MODE=\"synthetic\"\n"
        "     或把 configs/aoi.yaml 的 data.mode 改为 synthetic（结果会写入同一 results/ 目录）"
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
