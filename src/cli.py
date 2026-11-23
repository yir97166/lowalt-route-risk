"""一条命令运行整条管线，或只跑其中某一阶段。

用法（仓库根目录）：

    python -m src.cli all              # 等价于 scripts/run_all.py：合成数据 → 出图 → 建图 → … → 情景
    python -m src.cli check            # pytest -q
    python -m src.cli baseline         # 只重跑最短路 baseline
    python -m src.cli pareto --config configs/aoi.yaml
    python -m src.cli all --dry-run    # 只打印将执行的命令，不运行

设计：CLI 不重复实现算法，只把既有脚本按阶段组织起来；每个阶段内部仍然是
可以单独运行的脚本，保证「单步可调试、整链可复现」。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 阶段 → 脚本（按执行顺序）
STAGES: dict[str, list[str]] = {
    "data": ["scripts/make_synthetic_data.py"],
    "figure": ["scripts/make_population_map.py"],
    "grid": ["scripts/make_grid_map.py"],
    "baseline": ["scripts/make_baseline.py"],
    "weighted": ["scripts/make_weighted.py"],
    "batch": ["scripts/make_batch.py"],
    "pareto": ["scripts/make_pareto.py", "scripts/make_pareto_detail.py"],
    "resolution": ["scripts/make_resolution.py"],
    "scenarios": ["scripts/make_scenarios.py"],
}


def plan(stage: str, config: str | None = None) -> list[list[str]]:
    """返回该阶段要执行的命令列表（纯函数，便于测试）。"""
    if stage == "all":
        cmd = [sys.executable, "scripts/run_all.py"]
        if config:
            cmd += ["--config", config]
        return [cmd]
    if stage == "check":
        return [[sys.executable, "-m", "pytest", "-q"]]
    if stage not in STAGES:
        raise SystemExit(f"未知阶段：{stage}；可选：{', '.join([*STAGES, 'all', 'check'])}")
    cmds = []
    for script in STAGES[stage]:
        cmd = [sys.executable, script]
        if config:
            cmd += ["--config", config]
        cmds.append(cmd)
    return cmds


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="低空航路规划原型：一条命令复现管线",
    )
    ap.add_argument("stage", choices=[*STAGES, "all", "check"], help="要运行的阶段")
    ap.add_argument("--config", default=None, help="配置文件路径（默认 configs/aoi.yaml）")
    ap.add_argument("--dry-run", action="store_true", help="只打印命令，不执行")
    args = ap.parse_args(argv)

    cmds = plan(args.stage, args.config)
    for cmd in cmds:
        print("$", " ".join(cmd), flush=True)
        if args.dry_run:
            continue
        proc = subprocess.run(cmd, cwd=ROOT)
        if proc.returncode != 0:
            print(f"命令失败（退出码 {proc.returncode}）：{' '.join(cmd)}", file=sys.stderr)
            return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
