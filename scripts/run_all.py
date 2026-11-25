r"""一键跑完整条可复现流程（合成数据，不联网）。

用法（项目根目录）：
    .\.venv\Scripts\python.exe scripts\run_all.py
    .\.venv\Scripts\python.exe -m src.cli all

顺序：合成人口 → 人口热力图 → 网格/空域掩膜 → 最短路 baseline
      → λ=1 加权对比 → 5 组批量 OD → λ 扫描/Pareto → Pareto 路线明细
      → 起点偏移敏感性 → 网格分辨率敏感性 → 遮蔽参数敏感性
      → 高度层/安全区尺寸情景敏感性。

每步打印用时；任一步非零退出即停止。
同时写 logs/run_all_<时间戳>.log 与 logs/run_all_<时间戳>.json（最新一份复制为 logs/latest.json）。
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config  # noqa: E402
from src.data import pick_population_path  # noqa: E402
from src.runlog import setup_logger, timestamp, write_summary  # noqa: E402

LOGS = ROOT / "logs"

BASE_STEPS: list[tuple[str, list[str]]] = [
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
    ("宽幅空域图（完整净空走廊）", ["scripts/make_airspace_wide.py"]),
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    stamp = timestamp()
    logfile = LOGS / f"run_all_{stamp}.log"
    log = setup_logger(logfile)
    cfg = load_config(ROOT / "configs" / "aoi.yaml")
    mode = os.environ.get("LOWALT_DATA_MODE") or cfg.data.get("mode", "real")
    pop_path = pick_population_path(cfg)
    meta = {
        "commit": _git_commit(),
        "data_mode": mode,
        "population_file": str(pop_path.relative_to(ROOT)),
        "population_bytes": pop_path.stat().st_size,
        "population_sha256": _sha256(pop_path),
        "python": sys.executable,
    }
    STEPS = ([] if mode == "real" else [("合成人口栅格", ["scripts/make_synthetic_data.py"])]) + BASE_STEPS
    log.info("Python: %s", sys.executable)
    log.info("Project: %s", ROOT)
    log.info("Commit: %s", meta["commit"])
    log.info("Data mode: %s", mode)
    log.info("Population: %s (%d bytes)", meta["population_file"], meta["population_bytes"])
    log.info("Population SHA256: %s", meta["population_sha256"])
    if mode == "real":
        log.info("跳过合成栅格生成（real 模式，直接读取 WorldPop）")

    steps: list[dict] = []
    total = 0.0
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    status = "ok"

    try:
        for i, (label, args) in enumerate(STEPS, start=1):
            cmd = [sys.executable, *args]
            log.info("[%d/%d] %s ...", i, len(STEPS), label)
            t0 = time.perf_counter()
            proc = subprocess.run(cmd, cwd=ROOT)
            dt = time.perf_counter() - t0
            total += dt
            record = {
                "step": i,
                "label": label,
                "command": args[0],
                "seconds": round(dt, 2),
                "exit": proc.returncode,
            }
            steps.append(record)
            if proc.returncode != 0:
                status = "failed"
                log.error("    FAILED (exit %d, %.1f s)", proc.returncode, dt)
                log.error("    查看上面的输出定位失败原因；日志：%s", logfile)
                break
            log.info("    ok (%.1f s)", dt)
    except KeyboardInterrupt:
        status = "interrupted"
        log.warning("收到 Ctrl+C，已中断；已完成 %d/%d 步", len(steps), len(STEPS))

    elapsed = round(sum(s["seconds"] for s in steps), 2)
    summary = {
        "status": status,
        "started_at": started,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "python": sys.executable,
        "metadata": meta,
        "steps_total": len(STEPS),
        "steps_done": len(steps),
        "elapsed_s": elapsed,
        "steps": steps,
    }
    write_summary(LOGS / f"run_all_{stamp}.json", summary)
    write_summary(LOGS / "latest.json", summary)

    if status == "ok":
        log.info("All %d steps finished in %.1f s.", len(STEPS), total)
        log.info("Outputs: figures/*.png, results/*.csv, data/processed/*")
        return 0
    log.error("停止于第 %d 步；summary 已写入 logs/", len(steps))
    return 130 if status == "interrupted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
