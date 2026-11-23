"""Day 12：CLI 入口的单元测试（只测命令编排，不真的跑管线）。"""
from __future__ import annotations

import sys
from pathlib import Path

from src.cli import STAGES, plan

ROOT = Path(__file__).resolve().parents[1]


def test_every_stage_script_exists() -> None:
    for scripts in STAGES.values():
        for script in scripts:
            assert (ROOT / script).is_file(), script


def test_all_delegates_to_run_all() -> None:
    cmds = plan("all")
    assert len(cmds) == 1
    assert cmds[0][1].endswith("scripts/run_all.py")


def test_check_runs_pytest() -> None:
    (cmd,) = plan("check")
    assert cmd[-2:] == ["-m", "pytest"] or cmd[1:3] == ["-m", "pytest"]
    assert "pytest" in " ".join(cmd)


def test_config_is_forwarded() -> None:
    cmds = plan("baseline", "configs/aoi.yaml")
    assert cmds[0][-2:] == ["--config", "configs/aoi.yaml"]


def test_pareto_runs_two_scripts_in_order() -> None:
    cmds = plan("pareto")
    assert len(cmds) == 2
    assert cmds[0][1].endswith("make_pareto.py")
    assert cmds[1][1].endswith("make_pareto_detail.py")


def test_stage_order_covers_pipeline() -> None:
    # 管线阶段顺序应与 run_all 的 12 步一致（粗检：至少覆盖数据到情景）
    assert list(STAGES) == [
        "data",
        "figure",
        "grid",
        "baseline",
        "weighted",
        "batch",
        "pareto",
        "resolution",
        "scenarios",
    ]
