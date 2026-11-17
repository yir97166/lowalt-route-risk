# 低空航路规划与地面风险评估原型
**Low-Altitude Route Planning with Ground Risk Assessment**

> 状态：Day 1 完成（2026-11-17：环境 + 数据 + 人口热力图；Day 2 起按 PLAN.md 继续）  
> 项目根目录：`C:\Users\弋昊阳\OneDrive\文档\deepseek-harness\default-workspace\lowalt-route-risk`  
> 负责人：弋昊阳  
> 用途：港澳硕士申请作品集 + 低空/UTM/适航方向能力证明

## 一句话

给定深圳两个起降点，在避开机场净空区和禁飞区的前提下，规划一条低空航路，并量化「地面人口暴露风险」与「飞行距离」的权衡。

## 为什么做

- 空管本科背景 + Python/运筹，需要一个「可验证的硬作品」，而不是只有课程名。
- 港理工 48007（低空经济）的 AAE5302 / AAE5108 / AAE5304 正好对应 UTM、低空空域、适航风险。
- 申请材料里，一张路线图 + 一条 Pareto 曲线，比「我自学了 UTM」有说服力。

## 范围（MVP）

- 区域：深圳中西部，bbox `[113.85, 22.48, 114.10, 22.65]`，约 25×19 km。
- 网格：200 m；高度层 60/90/120 m AGL；8 邻域 + 垂直边。
- 5 组起降点；3 种 λ；3 种高度；3 种禁飞缓冲。
- 不做：实时、天气、完整 SORA 审定、UI、多机协同。

## 数据

- 人口：WorldPop 2020 中国 100 m（或 GHSL 2020）。
- 地图：OpenStreetMap（仅作底图/背景，可选；不参与路由）。
- 禁飞区：手工多边形（宝安机场 5 km 缓冲 + 2 个示意敏感区），标注 `illustrative only`。
- 降级：`scripts/make_synthetic_data.py` 生成合成人口/城市网格，保证 pipeline 可跑。

## 方法

1. 200 m 网格 + 3 层高度 → 3D 图。
2. 地面风险 = 人口密度 × 后果 × (1 − 遮蔽) × 高度因子；归一化 0–1。
3. 边代价 = 长度 × (1 + λ × 风险) + 禁飞硬惩罚。
4. 基线 λ=0；方案 λ=1；λ 扫描得 Pareto。
5. 5 组 OD、3 高度、3 缓冲的敏感性分析。
6. 单元测试：风险函数、图构建、禁飞掩膜、路线合法性。

## 产出

- `src/` 可复现代码；`configs/aoi.yaml` 配置；`notebooks/` 探索。
- 3 张图：人口风险热力图、路线对比图、Pareto 曲线。
- 6–8 页中文报告 + 1 页英文摘要。
- 3 分钟英文讲解视频（建议）。
- CV bullet + PS 段落。

## 成功标准

- 新克隆 10 分钟内跑通（带样本数据）。
- 路线 0 次穿过禁飞区。
- 相比最短路，人口暴露风险降低 ≥30%，距离增加 ≤20%（目标值，跑完按实际数据调整）。
- 报告写清假设、局限、失败模式，不冒充官方适航审定。

## 目录

```
lowalt-route-risk/
├─ README.md
├─ SESSION_BRIEF.md      # 新对话的第一条消息
├─ PLAN.md               # 21 天计划
├─ requirements.txt
├─ configs/aoi.yaml
├─ docs/spec.md          # 设计说明
├─ docs/data_sources.md  # 数据来源与许可
├─ scripts/
├─ src/
├─ notebooks/
├─ tests/
├─ data/raw/             # 不入库
├─ data/processed/       # 不入库
├─ figures/
└─ report/
```

## 怎么开始

```powershell
# 1) 环境（Python 3.12）
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2) 合成人口数据（无需联网）
.\.venv\Scripts\python.exe scripts\make_synthetic_data.py

# 3) 人口热力图 + 网格人口表
.\.venv\Scripts\python.exe scripts\make_population_map.py
```

真实数据：把 WorldPop 100 m GeoTIFF 放到 `data/raw/worldpop/chn_ppp_2020_100m.tif`，
去掉 `--synthetic` 重跑第 3 步即可（`src/data.py` 会自动优先使用真实栅格）。

## Day 1 记录（2026-11-17）

- **环境**：Python 3.12.10 + `.venv`；依赖 12 个，`pip check` 通过。
  默认 PyPI 源在本机卡住 14 分钟（缓存锁 + 解析回溯），改用清华镜像后 2 分钟装完。
- **数据**：WorldPop 2020 中国约束版为单个 625 MB GeoTIFF，range 请求 4 MB 超 90 s 未返回，
  判定为当天不可用，按计划降级为**合成数据**（5 个高斯人口团，标定到深圳量级：
  AOI 内约 512 万人，峰值约 1,250 人/100 m 像元）。
- **结果**：网格 128 列 × 98 行（200 m，EPSG:32649），非零人口格 12,197 个，
  p95 = 1,794 人/格，最大格 4,471 人；60 m 风险面最大值 0.700。
- **图**：`figures/00_population.png`。宝安机场 5 km 净空圈圆心在 AOI 西侧，
  图上只露出左边缘一小段弧线，属正常现象；两个（示意）敏感区多边形完整可见。
- **偏差与说明**：禁飞区全部 `illustrative only`，不是官方数据；人口为合成数据，
  仅用于跑通方法与出图，不能用于任何实际运行决策。详见 `docs/assumptions.md`。

