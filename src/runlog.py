"""轻量运行日志：每一步的开始/结束/耗时写到 logs/，并汇总成 JSON。

设计目标（Day 13）：
- 失败时能定位到「第几步、哪条命令、退出码」；
- 成功时留下一份机器可读的 summary，便于对比多次运行的耗时；
- 不引入第三方依赖，不改变各脚本原有的 stdout 行为。
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(logfile: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """返回带控制台 + 文件双输出的 logger；同名 logger 会先清空旧 handler。"""
    logger = logging.getLogger("lowalt")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if logfile is not None:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(logfile, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def write_summary(path: Path, payload: dict) -> None:
    """原子写 JSON（先写临时文件再替换），失败时也不留半截文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
