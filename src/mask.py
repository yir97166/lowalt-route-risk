"""禁飞区硬掩膜、邻接规则与路径几何验证。

设计原则（v1.2，按专家意见）：
- 禁飞区是**硬约束**：与禁飞区有任何重叠的格子一律不可通行（保守）。
- 对角边要求两个正交邻格都可通行，防止「切角」穿过禁飞区。
- 路线输出后用独立的几何库（shapely）做相交检查，不依赖掩膜实现本身。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.geometry.base import BaseGeometry

from .config import Config
from .grid import Grid, point_to_metric


def _corridor_geometry(cfg: Config, z) -> Polygon:
    """跑道净空走廊：沿真方位拉出「跑道长 + 端外延伸」×「2×半宽」的矩形。"""
    to_metric = Transformer.from_crs(cfg.crs_input, cfg.crs_metric, always_xy=True)
    cx, cy = to_metric.transform(z.center[0], z.center[1])  # type: ignore[index]
    b = np.deg2rad(float(z.bearing_deg))
    ax, ay = float(np.sin(b)), float(np.cos(b))        # 沿跑道方向（北为 0°，顺时针）
    px, py = float(np.cos(b)), float(-np.sin(b))       # 右手法向
    half_len = float(z.runway_length_m) / 2.0 + float(z.end_extension_m)
    hw = float(z.half_width_m)
    corners = [
        (cx + ax * half_len + px * hw, cy + ay * half_len + py * hw),
        (cx + ax * half_len - px * hw, cy + ay * half_len - py * hw),
        (cx - ax * half_len - px * hw, cy - ay * half_len - py * hw),
        (cx - ax * half_len + px * hw, cy - ay * half_len + py * hw),
    ]
    return Polygon(corners)


def zone_geometries(cfg: Config) -> list[tuple[str, BaseGeometry]]:
    """把空域约束转成 UTM 米制几何（含 hard=False 的受控区）。"""
    to_metric = Transformer.from_crs(cfg.crs_input, cfg.crs_metric, always_xy=True)
    out: list[tuple[str, BaseGeometry]] = []
    for z in cfg.no_fly:
        if z.kind == "circle":
            cx, cy = to_metric.transform(z.center[0], z.center[1])  # type: ignore[index]
            geom: BaseGeometry = Point(cx, cy).buffer(float(z.radius_m), quad_segs=64)
        elif z.kind == "runway_corridor":
            geom = _corridor_geometry(cfg, z)
        else:
            coords = [to_metric.transform(lon, lat) for lon, lat in z.vertices]
            geom = Polygon(coords)
            if not geom.is_valid:
                geom = geom.buffer(0)
        out.append((z.name, geom))
    return out


def hard_zone_geometries(cfg: Config) -> list[tuple[str, BaseGeometry]]:
    """只取 hard=True 的区，用于不可通行掩膜与路径验证。"""
    names = {z.name for z in cfg.no_fly if z.hard}
    return [(name, g) for name, g in zone_geometries(cfg) if name in names]


def _mask_from_geometries(grid: Grid, geoms: list[BaseGeometry]) -> np.ndarray:
    blocked = np.zeros(grid.shape, dtype=bool)
    if not geoms:
        return blocked
    union = unary_union([g for g in geoms if not g.is_empty])
    if union.is_empty:
        return blocked
    prepared = prep(union)
    minx, miny, maxx, maxy = union.bounds
    cell = grid.cell_m
    col_lo = max(int(np.floor((minx - grid.x0) / cell)), 0)
    col_hi = min(int(np.floor((maxx - grid.x0) / cell)) + 1, grid.cols)
    row_lo = max(int(np.floor((grid.y1 - maxy) / cell)), 0)
    row_hi = min(int(np.floor((grid.y1 - miny) / cell)) + 1, grid.rows)
    for r in range(row_lo, row_hi):
        y_bottom, y_top = grid.y_edges[r + 1], grid.y_edges[r]
        for c in range(col_lo, col_hi):
            cell_box = box(grid.x_edges[c], y_bottom, grid.x_edges[c + 1], y_top)
            if prepared.intersects(cell_box):
                blocked[r, c] = True
    return blocked


def blocked_mask(cfg: Config, grid: Grid) -> np.ndarray:
    """返回 (rows, cols) 布尔掩膜，True = 不可通行（只算 hard=True 的区）。

    判定：格子正方形与任一硬禁飞区相交即不可通行（含只压到一角），偏保守。
    """
    return _mask_from_geometries(grid, [g for _, g in hard_zone_geometries(cfg)])


def restricted_mask(cfg: Config, grid: Grid) -> np.ndarray:
    """受控/需审批区（hard=False，如机场净空保护区）覆盖的格子。"""
    names = {z.name for z in cfg.no_fly if not z.hard}
    geoms = [g for name, g in zone_geometries(cfg) if name in names]
    return _mask_from_geometries(grid, geoms)


def neighbors(
    grid: Grid,
    blocked: np.ndarray,
    row: int,
    col: int,
    connectivity: int = 8,
) -> list[tuple[int, int]]:
    """返回可通行的相邻格（不含自身）。

    对角邻居要求两个正交邻格都畅通，避免斜边切过禁飞区角点。
    """
    out: list[tuple[int, int]] = []
    steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if connectivity == 8:
        steps += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    for dr, dc in steps:
        r, c = row + dr, col + dc
        if not (0 <= r < grid.rows and 0 <= c < grid.cols):
            continue
        if blocked[r, c]:
            continue
        if dr != 0 and dc != 0:
            if blocked[row, col + dc] or blocked[row + dr, col]:
                continue
        out.append((r, c))
    return out


@dataclass(frozen=True)
class SnapResult:
    row: int
    col: int
    x: float
    y: float
    offset_m: float  # 原始点 → 格心的平面距离
    lon: float
    lat: float


def nearest_free_cell(
    cfg: Config,
    grid: Grid,
    blocked: np.ndarray,
    lon: float,
    lat: float,
) -> SnapResult:
    """把经纬度点吸附到最近的可通行格心，并记录偏移量。"""
    x, y = point_to_metric(cfg, lon, lat)
    free = ~blocked
    rows, cols = np.nonzero(free)
    if rows.size == 0:
        raise ValueError("没有可通行格，检查禁飞区是否覆盖了整个 AOI")
    cx, cy = grid.xs[cols], grid.ys[rows]
    d2 = (cx - x) ** 2 + (cy - y) ** 2
    i = int(np.argmin(d2))
    r, c = int(rows[i]), int(cols[i])
    to_geo = Transformer.from_crs(cfg.crs_metric, cfg.crs_input, always_xy=True)
    glon, glat = to_geo.transform(float(cx[i]), float(cy[i]))
    return SnapResult(
        row=r,
        col=c,
        x=float(cx[i]),
        y=float(cy[i]),
        offset_m=float(np.sqrt(d2[i])),
        lon=float(glon),
        lat=float(glat),
    )


def path_line(cells: list[tuple[int, int]], grid: Grid) -> LineString:
    """把格心序列转成米制折线。"""
    if len(cells) < 2:
        raise ValueError("路径至少需要 2 个格")
    return LineString([(float(grid.xs[c]), float(grid.ys[r])) for r, c in cells])


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    crossings: int
    length_m: float
    min_clearance_m: float
    issues: tuple[str, ...]


def validate_path(
    cells: list[tuple[int, int]],
    grid: Grid,
    cfg: Config,
    blocked: np.ndarray | None = None,
) -> ValidationResult:
    """独立验证一条路径：几何相交、格间步长、禁飞格。

    与掩膜实现解耦：这里直接用 shapely 判断折线是否穿过禁飞区。
    """
    issues: list[str] = []
    zones = hard_zone_geometries(cfg)
    union = unary_union([g for _, g in zones]) if zones else None

    # 1) 相邻步长合法（四邻或八邻）
    for a, b in zip(cells, cells[1:]):
        dr, dc = abs(a[0] - b[0]), abs(a[1] - b[1])
        if max(dr, dc) != 1:
            issues.append(f"格间步长非法：{a} → {b}")

    # 2) 不经过禁飞格
    if blocked is not None:
        for r, c in cells:
            if blocked[r, c]:
                issues.append(f"路径经过禁飞格：({r}, {c})")
                break

    # 3) 折线与禁飞区几何相交（逐段计数）
    crossings = 0
    min_clearance = float("inf")
    if union is not None and not union.is_empty:
        line = path_line(cells, grid)
        for p, q in zip(cells, cells[1:]):
            seg = LineString(
                [(float(grid.xs[p[1]]), float(grid.ys[p[0]])),
                 (float(grid.xs[q[1]]), float(grid.ys[q[0]]))]
            )
            if seg.intersects(union):
                crossings += 1
        min_clearance = float(line.distance(union))
        if crossings:
            issues.append(f"{crossings} 段折线与禁飞区相交")
        if min_clearance <= 0.0:
            issues.append("路径与禁飞区距离为 0")

    length_m = 0.0
    for a, b in zip(cells, cells[1:]):
        dx = float(grid.xs[b[1]] - grid.xs[a[1]])
        dy = float(grid.ys[b[0]] - grid.ys[a[0]])
        length_m += float(np.hypot(dx, dy))

    return ValidationResult(
        ok=not issues,
        crossings=crossings,
        length_m=length_m,
        min_clearance_m=min_clearance,
        issues=tuple(issues),
    )


def path_to_lonlat(cells: list[tuple[int, int]], grid: Grid, crs_input: str) -> np.ndarray:
    """格心序列转 WGS84 (N, 2) 数组，供绘图/导出。"""
    to_geo = Transformer.from_crs(grid.crs, crs_input, always_xy=True)
    lons, lats = to_geo.transform([float(grid.xs[c]) for _, c in cells],
                                  [float(grid.ys[r]) for r, _ in cells])
    return np.column_stack([lons, lats])
