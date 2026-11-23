# 低空航路规划与人口暴露权衡分析原型
**Low-Altitude Route Planning with a Population-Exposure Proxy**

> 仓库：<https://github.com/yir97166/lowalt-route-risk>
> 状态：**v0.2（Day 1–9 完成，2026-11-17 至 11-22）**
> 用途：港澳硕士申请作品集（低空经济 / UTM 方向），证明「方法—数据—验证」能跑通、能复现。
>
> **声明**：本项目计算的是「人口暴露代理值」，不是坠机风险、人员伤亡概率或 SORA 地面风险等级；
> 所有禁飞区与净空区均为示意或公开资料近似；不构成适航审定、运行许可、合规判断或任何实际飞行依据。

## 一句话

给定深圳中西部两个起降点，在避开硬禁飞区的前提下，比较「最短可行路线」与「低暴露路线」，
量化「飞行距离」与「累计人口暴露代理值」之间的权衡，并检验该权衡对偏好权重 λ、网格分辨率是否稳定。

## 核心结果（Week 1，可复算）

| 指标 | 结果 | 来源 |
|---|---|---|
| 研究区 / 网格 | 25×19 km，200 m，12,544 格（EPSG:32649） | `configs/aoi.yaml` |
| 空域约束 | 硬禁飞 4,982 格（39.7%）：机场净空走廊 4,706 + 梧桐山 144 + 水库 132 | `figures/01_grid_nofly.png` |
| 核心 OD 最短路 | 罗湖—福田 7.014 km，绕行率 1.051，0 次穿越 | `results/baseline.csv` |
| 扩展 OD | 4 组端点落在机场净空区内，判不可达（不是把端点挪走） | `results/baseline.csv` |
| λ=1 加权 | 核心 OD 长度 0.00% 变化，C 4,387.8 → 4,326.0（−1.4%） | `results/compare.csv` |
| λ 扫描 | 21 档 λ → 7 个不同解、6 个切换点；长度 7.014–9.140 km，C 2.609–4.388 | `results/pareto.csv`、`results/pareto_routes.csv` |
| 分辨率敏感性 | 100 / 200 / 400 m：沿路人口密度均下降（−11.2% / −6.2% / +1.0%） | `results/resolution.csv` |
| 吸附偏移敏感性 | 起终点整体平移 ±0.5 格：C 最大变动 100 m ±2.0% / 200 m ±3.2% / 400 m ±9.2% | `results/origin_shift_summary.csv` |
| 工程验证 | pytest **52 项**；12 步一键流程 124 s；CSV/PNG 可逐字节复现 | 见下 |

> 人口为合成数据（WorldPop 625 MB 当日无法稳定下载，按计划降级）。上表只证明方法链路与可复现性，
> **不代表深圳真实人口或真实风险**。

## 快速开始（一条命令）

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.\.venv\Scripts\python.exe scripts\run_all.py
```

实测：安装约 2 分钟，全流程 8 步 **63.4 s**，产出 `figures/00–07`、`results/*.csv`、`data/processed/*`。
单独重跑某一步时，脚本彼此独立，见 `scripts/`。

接入真实数据：把 WorldPop 100 m GeoTIFF 放到 `data/raw/worldpop/chn_ppp_2020_100m.tif` 并重跑，
`src/data.py` 会自动优先使用真实栅格，无需改代码。

## 方法（v1.2）

1. **网格**：200 m；8 邻域，对角移动要求两个正交邻格都畅通（防切角）。
2. **约束**：禁飞区删节点/删边；起终点吸附到最近可通行格并记录 `snap_offset_m`；路线用独立几何库复核 0 穿越。
3. **暴露代理**：`pop_norm × (1 − shelter) × alt_factor`，`pop_norm = min(pop/p95, 1)`；核心实验固定 60 m。
4. **边权**：`长度 × (1 + λ × 暴露)`；λ 无量纲偏好权重，不是能耗或时间。
5. **求解与对比**：λ=0 为最短路 baseline；λ=1 对比；λ=0–2 扫描得到非支配解（Pareto 前沿）。

## 范围与边界（MVP）

- 做：2D 网格路线、硬禁飞、人口暴露代理、λ 与分辨率敏感性、单元测试、一键复现。
- 不做：适航/合规判定、真实飞行航路、通信干扰/天气/空中相撞、多机协同、实时调度、UI。
- 机场净空保护区按深公规〔2017〕3 号尺寸建模（跑道中线两侧各 10 km、端外 20 km）。
  通告第一条明确「**严禁**……施放……无人机」，因此按**硬禁飞**处理（`hard: true`），
  走廊内 4,706 格全部不可通行；核心案例因此改用净空区外的罗湖—福田。
  机场周边 4 组扩展 OD 的端点落在走廊内，按「不可达」如实记录——这本身是结论：
  **现有机场布局下，起降点不宜设在净空保护区内。**

## 目录

```
lowalt-route-risk/
├─ README.md               # 本文件
├─ PLAN.md                 # 21 天计划（v1.2）
├─ configs/aoi.yaml        # 区域、网格、禁飞/净空、5 组 OD
├─ src/                    # config / grid / data / risk / mask / graph / router / viz
├─ scripts/                # 数据生成、各实验结果、run_all.py 一键复现
├─ tests/                  # mask / graph / router，共 20 项
├─ docs/                   # 设计、假设、决策、数据来源、日志、周报说明
├─ figures/                # 00–07 核心图与敏感性图
├─ results/                # baseline / compare / pareto / resolution / 参数敏感性 CSV
├─ data/raw|processed/     # 原始数据（不入库）与处理结果
└─ report/                 # 报告与视频（后续）
```

## 文档索引

| 文件 | 内容 |
|---|---|
| `docs/spec.md` | 设计说明与模块职责 |
| `docs/indicator_definition.md` | **指标定义与单位**：C（代理·米）、E、ρ̄、λ 量纲、可说/不可说口径 |
| `docs/pareto_reading.md` | **Pareto 明细与去重规则**：3 个解的表、切换点、读法陷阱 |
| `docs/assumptions.md` | 建模假设、不适用范围（v0.2） |
| `docs/decisions.md` | 15 条关键决策：决定/理由/来源/日期 |
| `docs/review_response.md` | 专家意见 18 条逐条响应与保留差异 |
| `docs/pitch.md` | 对外介绍：一句话 / 30 秒 / 2 分钟 / 5 个问题 |
| `docs/data_sources.md` | 数据来源、许可与引用方式 |
| `docs/progress_log.md` | Day 1–6 开发日志（含全部实测数字） |
| `docs/contributions.md` | 人工核对记录（贡献台账） |
| `docs/ownership_and_use.md` | **归属证据链与用途**：怎么证明是自己做的、能拿它干什么、署名模板 |

## 局限（写报告时必须保留）

- 人口为**合成数据**，绝对数字不代表深圳；所有结论只在这套数据内成立。
- 净空保护区按「严禁」作硬约束，但这仍是**模型简化**，不构成对具体飞行是否合法的判断。
- 机场净空安全区按**单一主区**处理，主区/副区未细分（2026-11-23 决定先不建，见 `docs/decisions.md` 第 22 条）。
- 核心实验仅 60 m 单层；90/120 m 仅作 Day 11 情景，标注为假设。
- λ=1 的「零距离代价」是等长 tie-break，不是优化效果好；真绕行从 λ≈1.1（s=0.30）开始。
- 400 m 网格两端吸附偏移 229/141 m（>100 m）；吸附位置能让 C 变动约 9%，
  与 λ 带来的差异同量级，故 400 m 只作稳健性对照，主结论用 200 m 并给区间。
- C 是等效暴露长度（代理·米），等于 Σ(边长 × 边暴露强度)，恒有 C ≤ L；
  不可与路线长度互换，不能写成「暴露 2,840 米」。定义见 `docs/indicator_definition.md`。
- 通信/电磁干扰、失效概率、坠落轨迹均未建模；只能做相对比较。
- 遮蔽系数 0.30 是假设不是文献值；敏感性显示它只平移阈值（0.975/1.100/1.275），
  不改变路线集合，但报告不能说「0.30 有依据」。

## Day 8 记录（2026-11-21，提前）

- 文献核对：docs/literature.md 收录 11 条可核验来源（SORA 2.5 草案、Primatesta 2019、
  Washington 2017 综述、la Cour-Harbo 2018、Bertrand 2023、WorldPop 等），
  逐条给 DOI；SORA 原文摘录表明「遮蔽」是缓解措施 M1(A)，不是固定系数。
- 参数敏感性：scripts/make_param_sensitivity.py，s=0.2/0.3/0.4 下路线集合相同，
  切换阈值 1.125 / 1.275 / 1.500，与 1/(1−s) 预测一致；
  图 igures/07_param_sensitivity.png。
- 文档：docs/assumptions.md §2/§3 补文献与敏感性；docs/decisions.md 第 16/17 条；
  本 README 补 Day 8 记录与文献索引。

## Day 9 记录（2026-11-22，提前）

- 净空区口径纠正：深公规〔2017〕3 号原文是「严禁」施放无人机，机场净空走廊改
  `hard: true`，硬禁飞格 4,982 格（39.7%）；核心案例换罗湖—福田（全程在走廊外）。
- 机场周边 4 组 OD 的端点落在走廊内（吸附 1,254–6,380 m），如实判不可达，
  不挪端点凑可达；4 组保留为「净空区内不宜设起降点」的反例。
- 测试补全：新增 `tests/test_risk.py`（9）、`tests/test_grid.py`（8）、
  `tests/test_config.py`（4），合计 **49 passed**。
- 全管线重跑（`scripts/run_all.py` 11 步）：硬禁飞 4,982 格、图 7,562 节点、
  核心 OD 7.014 km、λ=1 C 4,387.8→4,326.0（−1.4%）、Pareto 7 解 6 切换点。
- 文档同步：README/PLAN/spec/assumptions/decisions/literature/pitch/pareto_reading
  全部改到「硬禁飞 + 罗湖—福田」口径。

## Day 10 记录（2026-11-22，提前）

- 批量 OD 重新设计：4 组机场向 OD 作反例；新增 5 组走廊外 OD——
  罗湖—福田（核心）、福田—罗湖、北站—福田、龙华—福田、布吉—罗湖。
- `src/config.py` 的 `ODPair` 增加 `role`（core / batch / infeasible_example），
  脚本按角色过滤，不再把反例混进批量统计。
- 新增 `scripts/make_batch.py`：5 组各跑 λ=0 / λ=1，独立几何校验，输出
  `results/od_summary.csv`、`figures/10_batch_od.png`。
- 结果：5 组全部可达、0 穿越；龙华—福田出现真权衡（+8.5% 距离换 C −36.6%），
  其余 4 组长度不变、只在等长解里降暴露（−1.4% ~ −3.1%）。

## Day 11 记录（2026-11-23，提前）

- 高度情景：同一暴露面乘 1.00 / 0.85 / 0.70 后重跑 λ 扫描。**路线序列完全不变**，
  只有阈值沿 λ 轴等比例平移——核心 OD 1.100 / 1.300 / 1.575（比例 = 1/alt_factor），
  C 也按同一系数缩放（4,387.8 → 3,729.6 → 3,071.4）。原因：没有垂直代价时，暴露均匀
  缩放等价于把 λ 换成 λ·f。所以「高度」在本模型里**不是独立结论，只是情景刻度**。
- 具体反例：龙华—福田在 60 m、λ=1 会出现 +8.5% 绕行（C −36.6%）；90/120 m 下阈值升到
  1.15 / 1.375，固定 λ=1 不再绕行——不能据此说「120 m 更安全」。
- 安全区尺寸情景：机场净空安全区的半宽/端外延伸 ×0.5 / ×1.0 / ×1.5 → 不可通行
  1,160（9.3%）/ 4,982（39.7%）/ 7,615（60.7%）；机场向 4 组 OD 可达 1/4 → 0/4 → 0/4；
  核心 OD 恒为 7.014 km。当前把整条安全区当主区（hard），空域规划里的主区/副区细分尚未建模。
- 新增 `scripts/make_scenarios.py`、`src/mask.py::scale_corridor`；图 11/12、表
  `scenario_altitude*.csv` / `scenario_safety_area.csv`；测试 52 项（新增缩放等价、安全区单调性）。
- 口径：只做情景敏感性；不写「高度越高越安全」，也不把安全区尺寸倍数当真实审批边界。

## 路线图

- [x] Day 1–6：数据 → 网格/空域 → 最短路 → 加权 → λ 扫描/Pareto → 分辨率敏感性
- [x] Day 7：周复盘 + README v0.1 + tag（2026-11-21 完成）
- [x] Day 8：文献与暴露模型细化（2026-11-21 提前完成）
- [x] Day 9：净空硬禁飞 + 核心 OD 更换 + 测试补全（49 项，2026-11-22 提前）
- [x] Day 10：5 组走廊外 OD 批量实验（2026-11-22 提前）
- [x] Day 11：高度层与安全区尺寸情景敏感性（2026-11-23 提前）
- [ ] Day 12–21：CLI/整理、文献综述、6–8 页报告、英文摘要、3 分钟视频、发布

## 引用

- JARUS (2024). *SORA 2.5 main body draft*, for external consultation.
- Primatesta, Rizzo & la Cour-Harbo (2019). Ground Risk Map for Unmanned Aircraft in Urban Environments. DOI: 10.1007/s10846-019-01015-z.
- Washington, Clothier & Silva (2017). A review of UAS ground risk models. DOI: 10.1016/j.paerosci.2017.10.001.
- la Cour-Harbo (2018). Quantifying Risk of Ground Impact Fatalities for Small Unmanned Aircraft. DOI: 10.1007/s10846-018-0853-1.
- Tatem (2017). WorldPop, open data for spatial demography. DOI: 10.1038/sdata.2017.4.
- 国务院、中央军委.《无人驾驶航空器飞行管理暂行条例》（第 761 号令，2024-01-01 施行）.
- WorldPop (2020). *Global 2000–2020 Constrained Individual Countries, 100 m*.
- 深圳市公安局. 深公规〔2017〕3 号《关于加强深圳机场净空区域安全保护的通告》.
- 民航局 AIP：ZGSZ 2A-1 / 6A-1 / 6A-2 / 2P-1（工作副本，正式引用以原始页为准）.

## 许可

代码 MIT；文档 CC BY 4.0。第三方数据与航图版权归原机构，仅作方法演示。
