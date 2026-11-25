"""为送审包生成 SHA256 清单（含覆盖范围说明）。"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python scripts/make_manifest.py <送审包目录> [输出文件]")
        return 2
    base = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else base / "SHA256SUMS.txt"
    files = sorted(p for p in base.rglob("*") if p.is_file() and p.resolve() != out)
    lines = [
        "# SHA256 清单（发送前校验）",
        f"# 覆盖范围: {base.name} 下全部 {len(files)} 个文件（报告/图/数据/文档/源码 zip/依赖/日志/版本说明）",
        "# 校验: Get-FileHash -Algorithm SHA256 <文件>  或  sha256sum -c SHA256SUMS.txt",
    ]
    for f in files:
        lines.append(f"{sha256(f)}  {f.relative_to(base).as_posix()}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"清单: {out} ({len(files)} 项)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
