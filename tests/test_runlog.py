"""Day 13：运行日志与 summary 的单元测试。"""
from __future__ import annotations

import json
import logging

from src.runlog import setup_logger, timestamp, write_summary


def test_logger_writes_to_file(tmp_path) -> None:
    logfile = tmp_path / "logs" / "run.log"
    logger = setup_logger(logfile)
    logger.info("hello step")
    for handler in logger.handlers:
        handler.flush()
    text = logfile.read_text(encoding="utf-8")
    assert "hello step" in text
    assert "INFO" in text


def test_logger_has_single_stream_handler(tmp_path) -> None:
    logger = setup_logger(tmp_path / "run.log")
    streams = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(streams) == 2  # 控制台 + 文件


def test_write_summary_roundtrip(tmp_path) -> None:
    path = tmp_path / "logs" / "summary.json"
    payload = {"status": "ok", "steps": [{"step": 1, "seconds": 0.5, "exit": 0}]}
    write_summary(path, payload)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == payload
    assert not path.with_suffix(".json.tmp").exists()


def test_timestamp_format() -> None:
    stamp = timestamp()
    assert len(stamp) == 15 and stamp[8] == "_"
    assert stamp[:8].isdigit() and stamp[9:].isdigit()
