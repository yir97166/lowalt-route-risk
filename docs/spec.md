# 设计说明：低空航路规划与地面风险评估原型

> 版本：v0.1（2026-11-17）  
> 状态：方向 A 已确认，开工前唯一设计依据  
> 项目根：`C:\Users\弋昊阳\OneDrive\文档\deepseek-harness\default-workspace\lowalt-route-risk`

## 1. 问题

给定深圳中西部两个起降点，在避开硬禁飞区的前提下，规划一条低空航路，使「地面人口暴露风险」与「飞行距离」的加权代价最小；并量化两者之间的权衡（Pareto 前沿），而不是只给一条“看起来合理”的线。机场净空保护区按官方尺寸单独统计覆盖率，标为「需审批」，不参与硬约束。

## 2. 目标与非目标

### 2.1 目标

1. 可复现：新机器克隆后 10 分钟内跑出第一张图。
2. 可解释：每个假设（人口、遮蔽、高度、后果）都能在报告中说明。
3. 可比较：基线（最短路）vs 风险规避路，给出距离、风险、绕行比例。
4. 可展示：一张路线图、一张风险热力图、一条 Pareto 曲线。
5. 可迁移：方法能平移到其他城市/其他风险图层，不依赖某个专有数据源。

### 2.2 非目标

- 不做完整 JARUS SORA 审定，不做适航符合性声明。
- 不做实时航路、不做天气、不做多机协同、不做 UI。
- 不使用任何非公开/涉密空域数据；禁飞区为示意多边形。
- 不追求新算法；用成熟的 Dijkstra/多目标扫描，把工程做扎实。

## 3. 用户与用途

- 直接用户：弋昊阳（项目作者），用于港澳硕士申请作品集、面试讲解、CV。
- 间接读者：招生老师/面试官，需要在 3 分钟内看懂问题、方法、结果、局限。
- 不做产品化；不面向真实飞行运行。

## 4. 数据

### 4.1 输入

| 数据 | 用途 | 来源 | 许可/备注 |
|---|---|---|---|
| 人口栅格 100 m | 地面风险 | WorldPop 2020 China（或 GHSL 2020） | CC BY 4.0；需裁剪 |
| OSM 道路/水域/机场 | 底图/背景（可选） | OpenStreetMap / Overpass | ODbL；不参与路由 |
| 禁飞/敏感区多边形 | 硬约束 | 手工绘制，`configs/aoi.yaml` | `illustrative only`，非官方 |
| 机场净空保护区 | 受控/需审批区（非硬约束） | 深公规〔2017〕3 号 + AIP 2A-1（ARP 113.8117, 22.6383） | 官方尺寸；模型作近似 |

### 4.2 坐标与分辨率

- 输入统一 WGS84（EPSG:4326）。
- 计算投影：EPSG:32649（UTM 49N），用于米制距离；深圳跨 49/50 带，本项目范围小，误差可忽略，报告中注明。
- 网格 200 m；人口栅格聚合到网格（面积加权平均）。
- 高度层 60/90/120 m AGL；地形按平地处理（局限写入报告）。

### 4.3 数据降级

若 WorldPop/OSM 下载失败或被墙：

- `scripts/make_synthetic_data.py` 生成：
  - 3–5 个高斯人口团（代表 CBD/居住区）；
  - 规则路网/水域（可选）；
  - 与 `configs/aoi.yaml` 同样的 bbox/网格。
- pipeline、图表、报告结构不变；报告中标注「合成数据版」。
- 第二周若网络恢复，换真实数据重跑，保留两版结果。

## 5. 模型

### 5.1 网格与图

- 网格：`rows × cols`，每个格子中心 `(x, y)`；3 层高度 `k=0,1,2`。
- 节点：`(row, col, k)`；有效节点 = 未落入禁飞区。
- 边：
  - 同层 8 邻域；对角边长度按实际米制距离。
  - 垂直边：相邻高度层，代价 `vertical_cost_m = 50`（等效米）。
- 起降点：投影到最近的有效节点；若落在禁飞区，报错并提示改点。

### 5.2 风险

- `pop_norm = min(pop / p95, 1.0)`，`p95` 为 AOI 内人口非零格子的 95 分位。
- `risk_cell = pop_norm × severity × (1 − shelter) × alt_factor`
  - `severity = 1.0`（MVP 常数；后续可按无人机动能分级）。
  - `shelter = 0.30`（MVP 常数；表示 30% 遮蔽/缓解）。
  - `alt_factor`：60 m=1.00，90 m=0.85，120 m=0.70（越高暴露越低，简化假设）。
- `risk_edge = 0.5 × (risk_u + risk_v)`。
- 指标：
  - `mean_risk = Σ(risk_edge × length) / Σ(length)`
  - `total_exposure = Σ(risk_edge × length)`（人·米代理量）

### 5.3 代价与约束

- `cost_edge = length_m × (1 + λ × risk_edge) + penalty`
- `penalty = 1e6` 若任一端点被禁飞掩膜阻断；否则 0。
- `λ`：0（只距离）到 2（重风险）；默认 1.0。
- 禁飞区：硬约束，任何穿过禁飞格的边不可用。
- 机场净空保护区：官方尺寸走廊（两侧各 10 km、端外 20 km），标为受控/需审批区，
  不参与硬掩膜，只统计覆盖率；Day 11 可对走廊宽度做 ±20% 情景。

### 5.4 路由与 Pareto

- 基线：`λ=0` 的 Dijkstra 最短路。
- 方案：`λ=1` 的风险规避路。
- Pareto：`λ ∈ [0, 2]`，步长 0.1；对每个 λ 求最短路，记录 `(distance, mean_risk)`；保留非支配点。
- 若最短路与风险路相同，说明风险梯度不足，调整 λ/高度/缓冲后重跑；报告如实写。

### 5.5 指标

| 指标 | 定义 |
|---|---|
| `distance_km` | 路径总长度 |
| `mean_risk` | 长度加权平均风险 |
| `total_exposure` | 风险 × 长度之和 |
| `detour_pct` | `(L_risk / L_base − 1) × 100` |
| `risk_reduction_pct` | `(1 − mean_risk_risk / mean_risk_base) × 100` |
| `runtime_s` | 单次路由耗时 |

## 6. 系统结构

```
src/
├─ config.py        # YAML → dataclass；路径/参数校验
├─ data.py          # 人口栅格读取/裁剪；OSM 可选；合成数据
├─ grid.py          # bbox → 网格；投影；起降点吸附
├─ risk.py          # 人口归一化、风险面
├─ graph.py         # 3D 图构建；禁飞掩膜；边权
├─ router.py        # Dijkstra；λ 扫描；Pareto；指标
├─ experiments.py   # 核心 OD 扫描 + 批量 OD；CSV
├─ viz.py           # folium 地图；matplotlib 热力图/Pareto
└─ cli.py           # prepare / route / experiments / figures
tests/
├─ test_risk.py
├─ test_grid.py
├─ test_graph.py
└─ test_router.py
```

接口约定：

- `load_config(path) -> Config`
- `build_grid(cfg) -> Grid`（含 `pop`, `risk_cell`, `blocked`, `x`, `y`）
- `build_graph(grid, cfg) -> nx.Graph`
- `shortest_path(G, origin, dest, weight) -> Path`
- `run_scenario(cfg, scenario) -> dict`
- `plot_route(...)`, `plot_pareto(...)`

## 7. 实验设计

| 编号 | 实验 | 变量 | 输出 |
|---|---|---|---|
| E1 | 基线 vs 暴露加权路 | 1 组核心 OD（深圳北—深圳湾），λ=0/1 | 对比表 + 路线图 |
| E2 | λ 扫描 | λ=0–2，步长 0.1 | Pareto 图 |
| E3 | 高度层（情景） | 60/90/120 m，仅敏感性 | 距离/暴露表 |
| E4 | 净空走廊宽度 | 官方 10 km 基准 ±20% | 覆盖率/暴露表 |
| E5 | 人口权重 | 0.5/1/2（可选） | 敏感性表 |

固定随机种子；所有结果写 `results/`（CSV），图写 `figures/`。

## 8. 验证

- 单元测试：风险归一化边界、网格吸附、禁飞掩膜、路线不穿禁飞。
- 复现：删除 `data/processed` 后按 README 重跑，结果一致。
- 敏感性：λ/高度/缓冲变化时，指标方向合理（风险↓、距离↑）。
- 视觉检查：路线不穿硬禁飞区；穿越净空区的路段单独标注（需审批）；热力图与人口分布一致。
- 明确声明：模型为示意，不构成任何运行/审定依据。

## 9. 风险与降级

| 风险 | 降级 |
|---|---|
| 数据下载失败 | 合成数据；第二周换真实数据 |
| GIS 依赖装不上 | 纯 numpy 网格 + matplotlib |
| 风险路=最短路 | 调 λ/高度/缓冲；报告写“无显著权衡” |
| 时间不足 | 10 天 MVP：2D、1 OD、3 图、4 页报告 |
| 结果不显著 | 如实报告；把“为什么不显著”写成分析 |

## 10. 交付物

- GitHub repo（公开）：代码、配置、样本数据、README、报告。
- `figures/00_population.png`、`01_routes.png`、`02_pareto.png`。
- `report/report_zh.pdf`（6–8 页）+ `report/abstract_en.md`（1 页）。
- `report/demo.mp4`（3 分钟英文，可选但建议）。
- CV bullet + PS 段落（写在 `report/application.md`）。

## 11. 验收标准

- [ ] 新克隆 10 分钟内跑通（带样本数据）。
- [ ] 路线 0 次穿过禁飞区。
- [ ] 基线 vs 风险路的距离/风险对比表。
- [ ] Pareto 图 + 至少 2 组敏感性结果。
- [ ] 报告含假设、局限、失败模式。
- [ ] 英文 3 分钟能讲清问题/方法/结果/局限。

## 12. 开放问题（默认决策）

| 问题 | 默认决策 |
|---|---|
| 用真实 OSM 底图吗？ | 可选；没有也能出图（matplotlib 网格底图） |
| 考虑地形吗？ | 不考虑；平地假设，写入局限 |
| 考虑天气吗？ | 不考虑；out of scope |
| 多机冲突吗？ | 不考虑；stretch goal |
| 风险模型要多复杂？ | MVP 用人口×遮蔽×高度；第二周可加后果分级 |
| 禁飞区数据来源？ | 手工示意；不碰非公开数据 |
