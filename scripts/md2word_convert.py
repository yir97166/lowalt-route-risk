"""把 report_zh.md 转成 md-to-word 契约格式（report_md2word.md）。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "report" / "report_zh.md"
OUT = ROOT / "report" / "report_md2word.md"

KEYS = [
    "jarus2024", "primatesta2019", "washington2017", "lacourharbo2018",
    "bertrand2023", "li2021", "feng2025", "ford2010", "tatem2017",
    "szgov2017", "caac2024",
]

REPORT_FIGS = {
    "13_airspace_wide.png": ("figures/report/fig1_airspace.png", "12.4cm"),
    "00_population.png": ("figures/report/fig2_population.png", "12.2cm"),
    "03_route_compare.png": ("figures/report/fig3_routes.png", "7.8cm"),
    "05_pareto.png": ("figures/report/fig4_pareto.png", "10.4cm"),
}

EQUATIONS = [
    r"pop\_norm = \min(pop/p95,\ 1)",
    r"e = pop\_norm \times severity \times (1 - shelter) \times alt\_factor",
    r"C = \sum l_e \times (e_a + e_b)/2",
    r"E = C / L",
]

CJK = re.compile(r"[\u4e00-\u9fff]")


def join_smart(parts: list[str]) -> str:
    out = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out and not (CJK.search(out[-1]) and CJK.search(p[0])):
            out += " "
        out += p
    return out


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines()
    out: list[str] = [
        "---",
        "bibliography: refs.bib",
        "csl: chinese-gb7714-2015-numeric.csl",
        "---",
        "",
    ]

    assert lines[0].startswith("# ")
    out.append("%% 文档标题 " + lines[0][2:].strip())
    out.append("")

    i = 1
    # 开头的引用行：副标题 + 说明
    quotes: list[str] = []
    while i < len(lines) and (not lines[i].strip() or lines[i].startswith(">")):
        if lines[i].startswith(">"):
            quotes.append(lines[i][1:].strip())
        i += 1
    if quotes:
        out.append("%% 副标题 " + quotes[0])
        for q in quotes[1:]:
            out.append("%% 普通 " + q)
        out.append("")

    para: list[str] = []
    in_refs = False
    in_code = False
    code_buf: list[str] = []

    def flush() -> None:
        nonlocal para
        if not para:
            return
        out.append("%% 正文 " + join_smart(para))
        out.append("")
        para = []

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped == "```":
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                if code_buf and "pop_norm" in code_buf[0]:
                    for k, eq in enumerate(EQUATIONS, 1):
                        out.append(f"$${eq}$$ {{#eq-{k}}}")
                        out.append("")
                else:
                    for cl in code_buf:
                        out.append("%% 普通 " + cl)
                    out.append("")
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if line.startswith("## "):
            title = line[3:].strip()
            flush()
            if title == "参考文献":
                in_refs = True
                i += 1
                continue
            if title == "摘要":
                out.append("%% 摘要标题 摘要")
                out.append("")
                i += 1
                buf: list[str] = []
                while i < len(lines):
                    t = lines[i].strip()
                    if not t:
                        i += 1
                        continue
                    if t.startswith("**关键词"):
                        if buf:
                            out.append("%% 摘要 " + join_smart(buf))
                            out.append("")
                        out.append("%% 关键词 " + t.replace("**", ""))
                        out.append("")
                        i += 1
                        break
                    if t.startswith("#"):
                        break
                    buf.append(t)
                    i += 1
                continue
            out.append("# " + title)
            out.append("")
            i += 1
            continue
        if line.startswith("### "):
            flush()
            out.append("## " + line[4:].strip())
            out.append("")
            i += 1
            continue

        if in_refs:
            i += 1
            continue

        m = re.match(r"!\[(图 \d+[^\]]*)\]\(([^)]+)\)", stripped)
        if m:
            flush()
            name = Path(m.group(2)).name
            path, width = REPORT_FIGS.get(name, (m.group(2), "13.5cm"))
            out.append(f"![](../{path}){{width={width}}}")
            out.append("")
            out.append("%% 图片题注 " + m.group(1).strip())
            out.append("")
            i += 1
            continue

        m = re.match(r"\*\*(表 \d+.*?)\*\*", stripped)
        if m:
            flush()
            out.append("%% 表格题注 " + m.group(1).strip())
            out.append("")
            i += 1
            continue

        if stripped.startswith("|"):
            flush()
            out.append(stripped)
            i += 1
            continue
        if not stripped:
            flush()
            i += 1
            continue

        if re.match(r"^[-*]\s", stripped) or re.match(r"^\d+\.\s", stripped):
            flush()
            out.append(stripped)
            out.append("")
            i += 1
            continue

        para.append(stripped)
        i += 1

    flush()
    out.append("%% 参考文献标题 参考文献")
    out.append("")
    text = "\n".join(out)

    def repl(m: re.Match[str]) -> str:
        n = int(m.group(1))
        return f"[@{KEYS[n - 1]}]" if 1 <= n <= len(KEYS) else m.group(0)

    text = re.sub(r"\[(\d{1,2})\]", repl, text)
    text = text.replace("式 (1)–(3)", "式 @eq-1 至 @eq-3")
    OUT.write_text(text, encoding="utf-8")
    print(f"written {OUT} ({len(text)} chars)")


if __name__ == "__main__":
    main()
