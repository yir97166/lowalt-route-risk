# 模拟审稿修改清单（第二轮）

> 对应 `docs/mock_review.md` 的 10 条优先级清单。状态：✅ 已修 / ⬜ 待做。
> 最后更新：2026-11-25

| # | 问题（审稿人） | 处理 | 状态 |
|---|---|---|---|
| 1 | R2-M5：4 组机场向 OD 不可达仅凭 300 m 吸附阈值推断 | `src/mask.py` 新增 `point_in_hard_zone` 与 `od_feasibility`：先 shapely `within` 判定端点，在内直接不可达；在外才吸附，>300 m 记 `snap_too_far`；CSV `note` 写真实原因；新增 2 项测试 | ✅ |
| 2 | R2-M2：加权和只给 supported 点 | 报告与图注改「ε-约束/非支配解」措辞，不再称「加权和最优」 | ⬜ |
| 3 | R2-m5：仓库无 81 档逐 λ CSV | 导出 `results/pareto_sweep_full.csv`（81 档 × 核心 OD，含长度、C、路线 hash） | ⬜ |
| 4 | R2-m13：p95 未做敏感性 | 对 p90/p95/p99 各跑一次核心 OD，记录 C 与阈值是否变化 | ⬜ |
| 5 | R2-m6：`exposure_km` 列名与单位冲突 | 全仓库改名 `exposure_proxy_m` 并同步脚本/文档 | ⬜ |
| 6 | R2-m7/m8：assumptions、indicator_definition、statistics_statement 仍写旧阈值/λ=1 等长 | 三份文档按真实数据口径同步 | ⬜ |

## 复核命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q          # 64 passed
.\.venv\Scripts\python.exe scripts\run_all.py    # 13 步
```

## 说明

第 1 项已完成并验证：4 组反例端点 `within=True`，核心 OD 两端 `False`；报告 §3.2/§4.2 改为几何判定表述，测试 62→64。核心数字未变（7.014→7.511 km，C −33.05%）。
