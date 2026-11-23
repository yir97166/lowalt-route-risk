# 3-minute English introduction (draft)

> 用途：申请作品集的 3 分钟英文讲解（Day 18 录屏用）；也可当面试自我介绍。
> 目标语速 140–150 wpm，全文约 430 词 ≈ 2 分 55 秒。
> 数字全部来自仓库（`README.md` / `results/`），录制时不要改口。

## 时间轴与画面

| 时间 | 画面 | 内容 |
|---|---|---|
| 0:00–0:25 | `figures/00_population.png` | 问题：送货无人机不能只挑最短航线 |
| 0:25–0:55 | 同一张图 + 网格 | 方法：200 m 网格、人口暴露代理、硬禁飞 |
| 0:55–1:35 | `figures/09_pareto_routes.png` | 核心结果：λ 阈值、距离与暴露的权衡 |
| 1:35–2:05 | `figures/10_batch_od.png` | 批量结果：龙华真绕行；机场 4 组不可达 |
| 2:05–2:35 | `figures/11_altitude_scenario.png` | 情景：高度只平移阈值，不是"越高越安全" |
| 2:35–3:00 | 终端跑 `python -m src.cli check` | 边界与可复现：62 项测试、12 步管线 |

## 逐字稿（可直接照读）

**[0:00] Hook**

Imagine a drone delivering medical samples across Shenzhen. The shortest route is a straight line — but it passes over the most crowded neighborhoods. Is that acceptable?

I built a small, reproducible prototype to study this trade-off: how much extra distance is worth paying to fly over fewer people.

**[0:25] What it is**

The study area is 25 by 19 kilometers in central-western Shenzhen, cut into a 200-meter grid. Each cell gets a population-exposure proxy from gridded population data. No-fly constraints are hard: blocked cells are removed from the graph, not penalized. Routes are computed with Dijkstra on a weighted cost: length times one plus lambda times exposure.

Lambda is the only knob: zero is shortest path; larger lambda means I care more about people below.

**[0:55] Core result**

My core case is Luohu to Futian, seven point zero one kilometers.

At lambda equal to one, the route gets seven percent longer — and cumulative exposure drops by thirty-three percent. Part of that comes from a tie-break at very small lambda: the same length, lower exposure. The honest threshold for a real detour is about lambda zero point eight.

So the deliverable is not a safer route; it is a distance–exposure curve.

**[1:35] Batch result**

I then tested five origin–destination pairs outside the airport zone. Three of them show real detours at lambda one. Longhua to Futian is the clearest: eight point five percent more distance for a thirty-five percent exposure reduction.

The four airport-bound pairs were infeasible: their endpoints fall inside the airport protection corridor. I report that as a finding: you should not place a vertiport inside the protected area.

**[2:05] Scenario, not conclusion**

For altitude, I multiplied exposure by an engineering factor at sixty, ninety and one hundred twenty meters. The route set does not change; the switch threshold simply shifts by one over the factor: zero point eight, zero point nine five, one point two. That is why I do **not** claim "higher is safer." Without climb cost and real climb data, altitude is a scale, not a conclusion.

**[2:35] Limits and close**

Three limits. Population is WorldPop 2020 — a modelled estimate, not a census, so absolute numbers still carry uncertainty. There is no failure probability, so this is exposure, not risk of injury. And communication interference is not modeled.

What is real: the pipeline, the geometric checks, and the reproducibility. Sixty-two tests, a twelve-step run in under two minutes, and the same hashes on a fresh clone.

This is a methods demo for a master's application — not an airworthiness or compliance assessment. Thank you.

## 录制提示

- 不要念公式符号；说 "length times one plus lambda times exposure"。
- 数字念法：7.014 → "seven point zero one"; 4,982 → "four thousand nine hundred eighty-two"；
  7.09% → "seven point one percent"；33.05% → "thirty-three percent"；0.825 → "zero point eight"。
- 每段之间停 0.5 秒，方便后期剪。
- 如果时间超了，先删 2:05 的高度段（它只是反例），保留核心结果和边界。
- 中文对照：`docs/pitch.md` 有 30 秒版和两分钟版，可互相校对口径。
