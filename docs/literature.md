# 文献与暴露模型依据（Day 8）

> 目的：把「人口暴露代理」放在已有研究的坐标里，说清楚我们借了什么、没做什么、
> 哪些参数仍然只是工程假设。**本文件只列真正查到并读过摘要/原文的条目**；
> 没核实的条目不写进正式报告。
>
> 检索方式：Crossref API 按题名/作者检索（2026-11-21），逐条拿 DOI；
> SORA 原文下载自 JARUS 官网并抽取正文核对；人口数据引 WorldPop 官方论文。
> 本机日期 2026-11-21，对应执行计划 Day 8（原定 11/25，提前到 11/21 完成）。

## 1. 参考条目（正式报告只引这些）

| # | 文献 | 类型 | 本文怎么用 | 本文不做什么 |
|---|---|---|---|---|
| R1 | JARUS, *Guidelines on Specific Operations Risk Assessment (SORA)*, Edition 2.5（main body draft, for external consultation, 2024-02 上传） | 标准草案 | 地面风险的概念框架：iGRC 由「最大人口密度 × 无人机尺寸/速度」决定；缓冲区；遮蔽作为缓解措施而非固定系数 | 不算 GRC、不算 SAIL、不写 SORA 文件包；不冒充合规 |
| R2 | Primatesta, S., Rizzo, A., la Cour-Harbo, A. (2019). *Ground Risk Map for Unmanned Aircraft in Urban Environments*. Journal of Intelligent & Robotic Systems, 97, 489–509. DOI: 10.1007/s10846-019-01015-z | 期刊论文 | 「把地面风险做成栅格地图、再在图上规划」这一思路的直接来源 | 不复现其人口—遮蔽—伤亡模型，不引用其具体参数 |
| R3 | Washington, A., Clothier, R. A., Silva, J. (2017). *A review of unmanned aircraft system ground risk models*. Progress in Aerospace Sciences. DOI: 10.1016/j.paerosci.2017.10.001 | 综述 | 说明地面风险模型一般由「暴露人口 × 撞击概率 × 致死率」组成；本文只做第一项 | 不做撞击概率与致死率 |
| R4 | la Cour-Harbo, A. (2018). *Quantifying Risk of Ground Impact Fatalities for Small Unmanned Aircraft*. Journal of Intelligent & Robotic Systems. DOI: 10.1007/s10846-018-0853-1 | 期刊论文 | 说明「真正的伤亡风险需要撞击能量/机体参数」，本文缺这一层 | 不计算伤亡概率，不设定无人机质量/下降速度 |
| R5 | Bertrand, S., Lala, M., Raballand, N. (2023). *Handling Uncertainties in Ground Risk Buffer Computation for Risk Assessment and Preparation of UAV Operations*. ICUAS 2023. DOI: 10.1109/icuas57906.2023.10156086 | 会议论文 | 支撑「缓冲区尺寸本身有不确定性」这一保留意见 | 不做概率缓冲区 |
| R6 | Li, X., Zhang, Y., Li, Y., Liu, Y. (2021). *An Air Route Network Planning Model of Logistics UAV Terminal Distribution in Urban Low Altitude Airspace*. Sustainability, 13(23), 13079. DOI: 10.3390/su132313079 | 期刊论文 | 城市低空物流航线网络 + 栅格化建模的同类工作 | 不做网络级/多机容量优化 |
| R7 | Feng, Y., Zhang, Y., Tang, Y., Wang, Y., Feng, Y., Zhong, Y. (2025). *Digital Low-Altitude Airspace UAV Path Planning and Operational Capacity Assessment in Urban Risk Environments*. Drones, 9(5), 320. DOI: 10.3390/drones9050320 | 期刊论文 | 近期「风险环境下的低空路径 + 容量」工作，用于报告相关工作一节 | 不做容量评估、不做数字空域 |
| R8 | Ford, A. T., McEntee, R. J. (2010). *Assessment of the Risk to Ground Population Due to an Unmanned Aircraft In-Flight Failure*. AIAA ATIO 2010. DOI: 10.2514/6.2010-9056 | 会议论文 | 早期「在飞失效—地面人口」风险评估的代表 | 不做失效树/可靠性分析 |
| R9 | Tatem, A. J. (2017). *WorldPop, open data for spatial demography*. Scientific Data, 4, 170004. DOI: 10.1038/sdata.2017.4 | 数据论文 | 人口栅格数据的官方引用；真实数据接入时引这一条 | 本次未接入真实 WorldPop（下载失败，用合成数据） |
| R10 | 深圳市公安局，《关于加强深圳机场净空区域安全保护的通告》（深公规〔2017〕3号，2017-03-14） | 地方规范性文件 | 机场净空保护区的官方范围：跑道中心线两侧各 10 km、跑道端外 20 km | 通告原文「严禁」施放无人机，模型按硬禁飞（hard: true）处理；仍不判断具体飞行是否获批 |
| R11 | 《无人驾驶航空器飞行管理暂行条例》（国务院、中央军委令第 761 号，2024-01-01 施行） | 行政法规 | 报告背景：120 m 真高、适飞空域、飞行活动申请的制度背景 | 不做合规判断；具体条文以原文为准 |

> 说明：R1 是 2.5 版**草案**（external consultation），不是正式生效版本；报告里必须写「draft」。
> R11 只用于制度背景，不逐条解释，避免把「条例怎么规定」说成我们的结论。

## 2. SORA 原文怎么说（核对摘录）

从 `data/raw/references/JARUS_SORA_Main_Body_v2.5_draft.pdf` 抽取，要点：

- 地面风险的目标水平：**低于每小时百万分之一（1E-6）的致死事故**（针对被飞越人群）。
- **iGRC（1–11）由「最大人口密度」和「无人机最大特征尺寸 + 最大巡航速度」共同决定**；
  人口密度按分档取值：`<25 / <250 / <2,500 / <25,000 / <250,000 / >250,000 ppl/km²`。
- 评估范围 = **operational volume + ground risk buffer**（默认 1:1 原则）。
- **遮蔽（sheltering）是缓解措施 M1(A)**，用来把「风险人口」降到下一档，
  不是像我们这样乘一个固定系数 0.30。

对应到本项目：

| SORA 概念 | 我们的做法 | 差距 |
|---|---|---|
| iGRC 分档 | 连续暴露值 0–1 | 我们不分档，也不映射到 GRC |
| 最大人口密度 | p95 归一化后的格值 | 我们用 p95 截断，不是分档上限 |
| ground risk buffer | 无 | 我们没有缓冲区，只有硬禁飞几何 |
| sheltering 缓解 | 常数 0.30 | 我们把它当模型系数，SORA 当缓解措施 |
| 1E-6 目标 | 无 | 我们不计算事故率，无法对照 |

**结论**：本项目只能称为「人口暴露代理 + 路径权衡」，不能称为 SORA 评估。
这一点已写入 `docs/assumptions.md` 与 README 的边界声明。

## 3. 遮蔽系数 0.30：不是找依据，而是做敏感性

既然 0.30 没有文献依据，Day 8 改为回答一个可验证的问题：
**换一个遮蔽系数，结论会不会翻？**

因为 `exposure = pop_norm × severity × (1 − s) × alt_factor`，s 只是常数乘子，
路线代价 `L × (1 + λ × exposure)` 等价于把 λ 放大/缩小 `(1 − s)` 倍。
理论预测：路线切换阈值 `λ*(s) ∝ 1 / (1 − s)`。

用 `scripts/make_param_sensitivity.py` 对 s = 0.2 / 0.3 / 0.4 各扫 λ（0–2，步长 0.025）：

| 遮蔽系数 s | 实测切换阈值 λ* | 按 1/(1−s) 预测 | 不同解个数 |
|---|---|---|---|
| 0.2 | 1.125 | 1.116 | 3 |
| 0.3 | 1.275 | 1.275 | 3 |
| 0.4 | 1.500 | 1.487 | 3 |

（核心 OD，60 m 单层；图 `figures/07_param_sensitivity.png`，数据
`results/param_sensitivity.csv`、`results/param_sensitivity_summary.csv`。）

**结论**：

1. 三组解的**路线集合完全相同**，只有切换阈值按 `1/(1−s)` 平移；
   所以 s 取 0.2 还是 0.4，不会改变「λ≈1.3 之前不绕路、之后才绕」这个定性结论。
2. 因此报告可以写「在 s=0.30 的假设下，阈值约 1.3」，但**不能写「遮蔽系数 0.30 有依据」**；
   也不能宣称 1.3 是普适阈值——它随 s 与网格分辨率变化。
3. 敏感性实验本身也说明：我们缺的是「遮蔽如何随建筑密度变化」的数据，
   不是缺一个更精确的常数。

## 4. 仍然没有依据的参数（报告必须标注）

| 参数 | 现状 | 处理 |
|---|---|---|
| 遮蔽系数 0.30 | 工程假设；SORA 只把遮蔽当缓解措施 | 做敏感性（本文第 3 节），报告标注假设 |
| 高度因子 0.85 / 0.70 | 无可引文献 | 核心实验只做 60 m 单层；90/120 m 仅情景，且标「假设」 |
| severity = 1.0 | 只做相对比较 | 保留，报告写「不折算伤亡」 |
| p95 归一化 | 抗离群点的工程选择 | 保留，报告写清分母 |
| 禁飞多边形 | 手工示意 | 报告标「示意」，机场用官方通告范围另标「受控」 |
| 通信/电磁干扰 | 无数据 | 不建模，写入局限；有数据可作第二层 |

## 5. 下一步（Day 9 起）

- Day 9：把「暴露加权 + 独立几何校验」补进单元测试覆盖矩阵。
- Day 10：5 组 OD 批量实验，报告里每人一组「任务背景 + 距离/暴露」。
- Day 11：高度层情景（明确写「无可信爬升代价，仅情景比较」）。
- 报告「相关工作」一节直接按本文件 R1–R9 展开，不再新增未核实引用。
