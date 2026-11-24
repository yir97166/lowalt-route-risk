"""把 report/report_zh.md 渲染成 Word/PDF 技术报告。

只支持本项目用到的 Markdown 子集：标题、段落、无序/有序列表、表格、
代码块、图片（带图注）、**粗体** 与 `行内代码`。
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "report" / "report_zh.md"
OUT = ROOT / "report" / "低空航路规划原型-技术报告-v1.0.docx"

CN_FONT = "宋体"
HEAD_FONT = "黑体"
EN_FONT = "Times New Roman"
MONO_FONT = "Consolas"


def set_font(style_or_run, size: float | None = None, bold: bool | None = None,
             color: str | None = None, mono: bool = False, head: bool = False) -> None:
    font = style_or_run.font
    font.name = MONO_FONT if mono else EN_FONT
    if size is not None:
        font.size = Pt(size)
    if bold is not None:
        font.bold = bold
    if color:
        font.color.rgb = RGBColor.from_string(color)
    # 中文字体需要单独设置 eastAsia
    rpr = style_or_run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), (HEAD_FONT if head else CN_FONT) if not mono else MONO_FONT)
    if not mono:
        rfonts.set(qn("w:ascii"), EN_FONT)
        rfonts.set(qn("w:hAnsi"), EN_FONT)


def shade(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_footer_page_number(section) -> None:
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("低空航路规划原型 · 技术报告 v1.0 · 第 ")
    set_font(run, 8.5, color="808080")
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run2 = p.add_run()
    set_font(run2, 8.5, color="808080")
    run2._r.append(fld_begin)
    run2._r.append(instr)
    run2._r.append(fld_end)
    run3 = p.add_run(" 页")
    set_font(run3, 8.5, color="808080")


INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*]+\*|`[^`]+`)")
CITE = re.compile(r"\[\d+\]")
FIG_MAP = {
    "13_airspace_wide.png": "figures/report/fig1_airspace.png",
    "00_population.png": "figures/report/fig2_population.png",
    "03_route_compare.png": "figures/report/fig3_routes.png",
    "05_pareto.png": "figures/report/fig4_pareto.png",
}


def add_rich(paragraph, text: str, size: float = 10.5, citations: bool = True) -> None:
    text = text.replace("\\*", "*").replace("\\_", "_")
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            run = paragraph.add_run(piece[2:-2])
            set_font(run, size, bold=True)
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            run = paragraph.add_run(piece[1:-1])
            set_font(run, size)
            run.italic = True
        elif piece.startswith("`") and piece.endswith("`"):
            run = paragraph.add_run(piece[1:-1])
            set_font(run, size - 0.5, mono=True)
        else:
            for seg in (CITE.split(piece) if citations else [piece]):
                if not seg:
                    continue
                if CITE.fullmatch(seg):
                    run = paragraph.add_run(seg)
                    set_font(run, size - 1.5)
                    run.font.superscript = True
                else:
                    run = paragraph.add_run(seg)
                    set_font(run, size)


def join_smart(parts: list[str]) -> str:
    out = parts[0]
    for nxt in parts[1:]:
        a, b = out[-1], nxt[0]
        if ("\u4e00" <= a <= "\u9fff") or ("\u4e00" <= b <= "\u9fff") \
                or a in "，。；：、）」』" or b in "，。；：、（（":
            out += nxt
        else:
            out += " " + nxt
    return out


def add_table(doc, rows: list[list[str]], keep_together: bool = False) -> None:
    cols = len(rows[0])
    table = doc.add_table(rows=len(rows), cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    tblPr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "autofit")
    tblPr.append(layout)

    # GB/T 三线表：上下粗线 + 表头下细线，无竖线
    borders = OxmlElement("w:tblBorders")
    for edge, sz, color in (("top", "12", "000000"), ("bottom", "12", "000000"),
                            ("insideH", "0", "FFFFFF"), ("insideV", "0", "FFFFFF"),
                            ("left", "0", "FFFFFF"), ("right", "0", "FFFFFF")):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single" if sz != "0" else "nil")
        el.set(qn("w:sz"), sz)
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)

    for r, row in enumerate(rows):
        for c, cell_text in enumerate(row):
            cell = table.cell(r, c)
            para = cell.paragraphs[0]
            para.paragraph_format.space_before = Pt(2)
            para.paragraph_format.space_after = Pt(2)
            para.paragraph_format.line_spacing = 1.0
            add_rich(para, cell_text.strip(), size=9, citations=False)
            if r == 0:
                for run in para.runs:
                    run.font.bold = True
                tcPr = cell._tc.get_or_add_tcPr()
                tcBorders = OxmlElement("w:tcBorders")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "8")
                bottom.set(qn("w:color"), "000000")
                tcBorders.append(bottom)
                tcPr.append(tcBorders)

    # 按内容长度分配列宽（总宽 17 cm）
    weights = []
    for c in range(cols):
        longest = max(len(str(row[c])) for row in rows)
        weights.append(min(max(longest, 6), 34))
    total = sum(weights)
    for c, cell in enumerate(table.columns[0].cells):
        pass
    for c in range(cols):
        w = Cm(17.0 * weights[c] / total)
        for r in range(len(rows)):
            table.cell(r, c).width = w

    # 表头跨页重复、行不拆分；小表整体不跨页
    trPr = table.rows[0]._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:tblHeader"))
    for idx, row in enumerate(table.rows):
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        if keep_together and idx < len(table.rows) - 1:
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.paragraph_format.keep_with_next = True


def add_image(doc, path: Path, caption: str) -> None:
    mapped = FIG_MAP.get(path.name)
    if mapped:
        path = ROOT / mapped
    pic_para = doc.add_paragraph()
    pic_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_para.paragraph_format.space_before = Pt(6)
    pic_para.paragraph_format.space_after = Pt(2)
    if "fig1" in path.name:
        width = Cm(14.8)
    elif "fig3" in path.name:
        width = Cm(10.2)
    else:
        width = Cm(13.5)
    pic_para.add_run().add_picture(str(path), width=width)
    pic_para.paragraph_format.keep_with_next = True
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    run = cap.add_run(caption)
    set_font(run, 8.5, color="404040")


def build() -> None:
    raw_lines = SRC.read_text(encoding="utf-8").splitlines()
    lines: list[str] = []
    in_code = False
    in_ref = False
    for raw in raw_lines:
        if raw.startswith("```"):
            in_code = not in_code
            lines.append(raw)
            continue
        if in_code:
            lines.append(raw)
            continue
        # 参考文献续行合并
        if raw.startswith("["):
            in_ref = True
            lines.append(raw.rstrip())
            continue
        if in_ref:
            if not raw.strip():
                in_ref = False
                lines.append("")
                continue
            if raw.lstrip().startswith("#"):
                in_ref = False
                lines.append(raw)
                continue
            lines[-1] = (lines[-1] + " " + raw.strip()).strip()
            continue
        # 列表续行合并
        if raw.startswith("  ") and lines and not re.match(r"^\s*\d+\.\s", raw):
            if lines[-1].lstrip().startswith("- "):
                lines[-1] = (lines[-1].rstrip() + raw.strip())
                continue
        lines.append(raw.rstrip())

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)

    styles = doc.styles
    normal = styles["Normal"]
    set_font(normal, 11)
    normal.paragraph_format.line_spacing = 1.42
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, color in (("Heading 1", 20, "1A1A1A"),
                              ("Heading 2", 13, "1A1A1A"),
                              ("Heading 3", 11.5, "1A1A1A")):
        st = styles[name]
        set_font(st, size, bold=True, color=color, head=True)
        st.paragraph_format.space_before = Pt(10 if name == "Heading 1" else 7)
        st.paragraph_format.space_after = Pt(4)
        st.paragraph_format.keep_with_next = True

    add_footer_page_number(section)

    i = 0
    in_code = False
    code_lines: list[str] = []
    first_h1 = True

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Cm(0.3)
                para.paragraph_format.space_before = Pt(2)
                para.paragraph_format.space_after = Pt(8)
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                para.paragraph_format.line_spacing = 1.0
                run = para.add_run("\n".join(code_lines))
                set_font(run, 9, mono=True)
            i += 1
            continue
        if in_code:
            code_lines.append(raw)
            i += 1
            continue

        if line.strip() == "\\pagebreak":
            doc.add_page_break()
            i += 1
            continue

        if not line.strip():
            i += 1
            continue

        if line.startswith("# "):
            para = doc.add_paragraph(line[2:].strip(), style="Heading 1")
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if first_h1 else WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                set_font(run, 17, bold=True, color="1A1A1A", head=True)
            first_h1 = False
            i += 1
            continue
        if line.startswith("## "):
            para = doc.add_paragraph(line[3:].strip(), style="Heading 2")
            for run in para.runs:
                set_font(run, 13, bold=True, color="1A1A1A", head=True)
            i += 1
            continue
        if line.startswith("### "):
            para = doc.add_paragraph(line[4:].strip(), style="Heading 3")
            for run in para.runs:
                set_font(run, 11.5, bold=True, color="1A1A1A", head=True)
            i += 1
            continue

        # 图片 + 图注
        m = re.match(r"!\[(.*?)\]\((.+?)\)$", line.strip())
        if m:
            caption, rel = m.group(1), m.group(2)
            path = (ROOT / rel).resolve()
            if path.exists():
                add_image(doc, path, caption)
            i += 1
            continue

        # 引用块（标题下的说明）
        if line.lstrip().startswith(">"):
            note_lines = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                note_lines.append(lines[i].lstrip()[1:].strip())
                i += 1
            note = doc.add_paragraph()
            note.paragraph_format.space_after = Pt(8)
            run = note.add_run(" ".join(x for x in note_lines if x))
            set_font(run, 8.5, color="404040")
            continue

        # 参考文献（悬挂缩进、小字号）
        if re.match(r"^\[\d+\]", line):
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0.7)
            para.paragraph_format.first_line_indent = Cm(-0.7)
            para.paragraph_format.space_after = Pt(1)
            para.paragraph_format.line_spacing = 0.9
            add_rich(para, line.strip(), size=8.8, citations=False)
            i += 1
            continue

        # 表格
        if line.lstrip().startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = [c for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"\s*:?-{2,}:?\s*", c) for c in cells):
                    rows.append([c.strip() for c in cells])
                i += 1
            if rows:
                add_table(doc, rows, keep_together=len(rows) <= 4)
                doc.add_paragraph().paragraph_format.space_after = Pt(0)
            continue

        # 列表
        if line.lstrip().startswith("- "):
            para = doc.add_paragraph(style="List Bullet")
            para.paragraph_format.space_after = Pt(2)
            add_rich(para, line.lstrip()[2:].strip())
            i += 1
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            num = int(re.match(r"^\s*(\d+)\.", line).group(1))
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0.75)
            para.paragraph_format.first_line_indent = Cm(-0.75)
            para.paragraph_format.space_after = Pt(2)
            add_rich(para, f"{num}. " + re.sub(r"^\s*\d+\.\s+", "", line).strip())
            i += 1
            continue

        # 普通段落（合并连续行）
        parts = [line.strip()]
        j = i + 1
        while j < len(lines):
            nxt = lines[j].strip()
            if not nxt or nxt.startswith(("#", "- ", "|", "```", "![")) or re.match(r"^\d+\.\s", nxt):
                break
            parts.append(nxt)
            j += 1
        para = doc.add_paragraph()
        para.paragraph_format.first_line_indent = Cm(0.74)
        add_rich(para, join_smart(parts))
        i = j

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"written: {OUT}")


if __name__ == "__main__":
    build()
