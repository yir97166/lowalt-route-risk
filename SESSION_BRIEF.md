# 新对话第一条消息（复制到 New Chat）

我在做一个低空航路规划的硬项目，项目根目录：

`C:\Users\弋昊阳\OneDrive\文档\deepseek-harness\default-workspace\lowalt-route-risk`

**背景**：我是中国民航大学交通运输（空管方向）2027 届本科生，正在申请 2027 fall 港澳低空/适航硕士（主攻港理工 48007），需要一份可复现的作品集项目。项目方向已确认（A）：深圳 25×19 km 区域，200 m 网格 + 3 层高度，人口风险 + 禁飞区，做低空航路规划与地面风险评估，量化安全-效率权衡。

**请先读**：
1. `README.md`
2. `docs/spec.md`
3. `PLAN.md`
4. `configs/aoi.yaml`

**然后按 `PLAN.md` 的 Day 1 开始**：
- 建 Python venv，装 `requirements.txt`
- 下载/合成数据（WorldPop、OSM、禁飞多边形）
- 跑出第一张人口风险热力图 `figures/00_population.png`
- 初始化 git，提交 v0.1

**约束**：
- 每天 2–3 小时，周末 5 小时；3 周完成（2026-11-18 至 2026-12-08）。
- 先做 MVP：2D 跑通再加高度层；不做 UI/实时/天气/多机。
- 数据下载失败就用 `scripts/make_synthetic_data.py` 的合成数据，方法不变。
- 所有代码要能在 Windows + Python 3.10+ 跑；中文注释可以，变量名用英文。
- 报告和 README 用中文，英文摘要另写。
- 不冒充官方适航审定；所有禁飞区/风险模型标注 `illustrative`。

**工作方式**：每完成一天，更新 `PLAN.md` 的进度，并把当天产出（图/表/代码）提交；遇到数据/依赖问题先给降级方案，不要卡住。不要重新讨论选题，方向已定。

现在开始 Day 1。
