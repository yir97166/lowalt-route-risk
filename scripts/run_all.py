r"""一键跑完 Week 1 全部可复现流程（合成数据，不联网）。

用法（项目根目录）：
    .\.venv\Scripts\python.exe scripts\run_all.py

顺序：合成人口 → 人口热力图 → 网格/空域掩膜 → 最短路 baseline
      → λ=1 加权对比 → 5 组批量 OD → λ 扫描/Pareto → Pareto 路线明细
      → 起点偏移敏感性 → 网格分辨率敏感性 → 遮蔽参数敏感性
      → 高度层/安全区尺寸情景敏感性。
每步打印用时；任一步非零退出即停止。
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS: list[tuple[str, list[str]]] = [
    ("合成人口栅格", ["scripts/make_synthetic_data.py"]),
    ("人口热力图 + 网格人口表", ["scripts/make_population_map.py"]),
    ("网格 + 空域约束 + 起终点吸附", ["scripts/make_grid_map.py"]),
    ("最短路 baseline（5 组 OD）", ["scripts/make_baseline.py"]),
    ("λ=1 暴露加权 vs baseline", ["scripts/make_weighted.py"]),
    ("5 组批量 OD 汇总（走廊外）", ["scripts/make_batch.py"]),
    ("λ 扫描 + Pareto", ["scripts/make_pareto.py"]),
    ("Pareto 路线明细（去重/切换点）", ["scripts/make_pareto_detail.py"]),
    ("起点偏移敏感性", ["scripts/make_origin_shift.py"]),
    ("网格分辨率敏感性", ["scripts/make_resolution.py"]),
    ("遮蔽参数敏感性（s=0.2/0.3/0.4）", ["scripts/make_param_sensitivity.py"]),
    ("高度层 / 安全区尺寸情景敏感性", ["scripts/make_scenarios.py"]),
]


def main() -> int:
    total = 0.0
    print(f"Python: {sys.executable}")
    print(f"Project: {ROOT}\n")
    for i, (label, args) in enumerate(STEPS, start=1):
        cmd = [sys.executable, *args]
        print(f"[{i}/{len(STEPS)}] {label} ...", flush=True)
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, cwd=ROOT)
        dt = time.perf_counter() - t0
        total += dt
        if proc.returncode != 0:
            print(f"    FAILED (exit {proc.returncode}, {dt:.1f} s)")
            return proc.returncode
        print(f"    ok ({dt:.1f} s)")
    print(f"\nAll {len(STEPS)} steps finished in {total:.1f} s.")
    print("Outputs: figures/*.png, results/*.csv, data/processed/*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
