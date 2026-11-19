"""读取 configs/aoi.yaml，转成强类型配置对象。

用法：
    from src.config import load_config
    cfg = load_config()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "configs" / "aoi.yaml"


@dataclass(frozen=True)
class GridConfig:
    cell_size_m: float = 200.0
    altitudes_m: tuple[int, ...] = (60, 90, 120)
    connectivity: int = 8
    vertical_cost_m: float = 50.0


@dataclass(frozen=True)
class RiskConfig:
    population_weight: float = 1.0
    severity: float = 1.0
    shelter: float = 0.30
    population_percentile: float = 95.0
    altitude_factor: dict[int, float] = field(default_factory=dict)
    lambda_values: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0)
    lambda_default: float = 1.0
    penalty: float = 1_000_000.0


@dataclass(frozen=True)
class NoFlyZone:
    """空域约束。circle / polygon / runway_corridor。

    hard=True 表示几何上不可通行；hard=False 表示「受控/需审批」区，
    只在报告与图中标注，不参与硬掩膜（例如机场净空保护区）。
    runway_corridor 用 centerline 中心点 + 方位 + 半宽 + 端外延伸描述。
    """

    name: str
    kind: str  # "circle" | "polygon" | "runway_corridor"
    note: str = ""
    hard: bool = True
    center: tuple[float, float] | None = None
    radius_m: float | None = None
    vertices: tuple[tuple[float, float], ...] = ()
    bearing_deg: float | None = None
    runway_length_m: float | None = None
    half_width_m: float | None = None
    end_extension_m: float | None = None

    def __post_init__(self) -> None:
        if self.kind == "circle" and (self.center is None or self.radius_m is None):
            raise ValueError(f"圆形禁飞区 {self.name} 缺少 center/radius_m")
        if self.kind == "polygon" and len(self.vertices) < 3:
            raise ValueError(f"多边形禁飞区 {self.name} 至少需要 3 个顶点")
        if self.kind == "runway_corridor":
            missing = [
                k for k, v in (
                    ("center", self.center),
                    ("bearing_deg", self.bearing_deg),
                    ("runway_length_m", self.runway_length_m),
                    ("half_width_m", self.half_width_m),
                    ("end_extension_m", self.end_extension_m),
                ) if v is None
            ]
            if missing:
                raise ValueError(f"跑道净空走廊 {self.name} 缺少字段：{missing}")


@dataclass(frozen=True)
class ODPair:
    name: str
    origin: tuple[float, float]  # (lon, lat) WGS84
    destination: tuple[float, float]


@dataclass(frozen=True)
class Config:
    project: str
    crs_input: str
    crs_metric: str
    aoi_name: str
    bbox: tuple[float, float, float, float]  # minx, miny, maxx, maxy (WGS84)
    grid: GridConfig
    risk: RiskConfig
    data: dict[str, str]
    no_fly: tuple[NoFlyZone, ...]
    od_pairs: tuple[ODPair, ...]
    root: Path

    def resolve(self, rel_path: str) -> Path:
        """把配置里的相对路径解析到项目根目录。"""
        p = Path(rel_path)
        return p if p.is_absolute() else self.root / p


def _as_bbox(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"aoi.bbox 必须是 [minx, miny, maxx, maxy]，得到 {value!r}")
    minx, miny, maxx, maxy = (float(v) for v in value)
    if not (minx < maxx and miny < maxy):
        raise ValueError(f"aoi.bbox 顺序错误：{value!r}")
    return minx, miny, maxx, maxy


def _as_no_fly(item: dict[str, Any]) -> NoFlyZone:
    kind = str(item.get("type", "")).lower()
    common = {
        "name": str(item["name"]),
        "kind": kind,
        "note": str(item.get("note", "")),
        "hard": bool(item.get("hard", True)),
    }
    if kind == "circle":
        center = tuple(float(v) for v in item["center"])  # type: ignore[arg-type]
        return NoFlyZone(
            **common,
            center=(center[0], center[1]),
            radius_m=float(item["radius_m"]),
        )
    if kind == "polygon":
        verts = tuple((float(x), float(y)) for x, y in item["vertices"])
        return NoFlyZone(**common, vertices=verts)
    if kind == "runway_corridor":
        center = tuple(float(v) for v in item["center"])  # type: ignore[arg-type]
        return NoFlyZone(
            **common,
            center=(center[0], center[1]),
            bearing_deg=float(item["bearing_deg"]),
            runway_length_m=float(item["runway_length_m"]),
            half_width_m=float(item["half_width_m"]),
            end_extension_m=float(item["end_extension_m"]),
        )
    raise ValueError(
        f"空域约束类型 {kind!r} 不支持（只支持 circle / polygon / runway_corridor）"
    )


def load_config(path: str | Path | None = None) -> Config:
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"配置文件不存在：{cfg_path}")
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    g = raw.get("grid", {})
    r = raw.get("risk", {})
    grid = GridConfig(
        cell_size_m=float(g.get("cell_size_m", 200)),
        altitudes_m=tuple(int(v) for v in g.get("altitudes_m", (60, 90, 120))),
        connectivity=int(g.get("connectivity", 8)),
        vertical_cost_m=float(g.get("vertical_cost_m", 50)),
    )
    risk = RiskConfig(
        population_weight=float(r.get("population_weight", 1.0)),
        severity=float(r.get("severity", 1.0)),
        shelter=float(r.get("shelter", 0.30)),
        population_percentile=float(r.get("population_percentile", 95)),
        altitude_factor={int(k): float(v) for k, v in r.get("altitude_factor", {}).items()},
        lambda_values=tuple(float(v) for v in r.get("lambda_values", (0.0, 0.5, 1.0, 1.5, 2.0))),
        lambda_default=float(r.get("lambda_default", 1.0)),
        penalty=float(r.get("penalty", 1e6)),
    )
    if grid.cell_size_m <= 0:
        raise ValueError("grid.cell_size_m 必须为正")
    if not 0.0 <= risk.shelter <= 1.0:
        raise ValueError("risk.shelter 必须在 [0, 1]")
    if not 0.0 < risk.population_percentile <= 100.0:
        raise ValueError("risk.population_percentile 必须在 (0, 100]")

    od_pairs = tuple(
        ODPair(
            name=str(item["name"]),
            origin=(float(item["origin"][0]), float(item["origin"][1])),
            destination=(float(item["destination"][0]), float(item["destination"][1])),
        )
        for item in raw.get("od_pairs", [])
    )
    if not od_pairs:
        raise ValueError("config 里没有 od_pairs")

    return Config(
        project=str(raw.get("project", "lowalt-route-risk")),
        crs_input=str(raw.get("crs_input", "EPSG:4326")),
        crs_metric=str(raw.get("crs_metric", "EPSG:32649")),
        aoi_name=str(raw.get("aoi", {}).get("name", "aoi")),
        bbox=_as_bbox(raw["aoi"]["bbox"]),
        grid=grid,
        risk=risk,
        data={str(k): str(v) for k, v in raw.get("data", {}).items()},
        no_fly=tuple(_as_no_fly(item) for item in raw.get("no_fly", [])),
        od_pairs=od_pairs,
        root=ROOT,
    )
