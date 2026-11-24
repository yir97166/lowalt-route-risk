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

CN_FONT = "微软雅黑"
MONO_FONT = "Consolas"


def set_font(style_or_run, size: float | None = None, bold: bool | None = None,
             color: str | None = None, mono: bool = False) -> None:
    font = style_or_run.font
    font.name = MONO_FONT if mono else CN_FONT
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
    rfonts.set(qn("w:eastAsia"), CN_FONT if not mono else MONO_FONT)


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
CITE = re.compile(r"(\[\d+(?:[–-]\d+)?(?:,\s*\d+)*\])")
FIG_MAP = {
    "13_airspace_wide.png": "figures/report/fig1_airspace.png",
    "00_population.png": "figures/report/fig2_population.png",
    "03_route_compare.png": "figures/report/fig3_routes.png",
    "05_pareto.png": "figures/report/fig4_pareto.png",
}


def add_rich(paragraph, text: str, size: float = 10.5, citations: bool = True) -> None:
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
                    run = paragraph.add_run(seg[1:-1])
                    set_font(run, size - 1.5)
                    run.font.superscript = True
                else:
                    run = paragraph.add_run(seg)
                    set_font(run, size)


def add_table(doc, rows: list[list[str]]) -> None:
    cols = len(rows[0])
    table = doc.add_table(rows=len(rows), cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True
    tblPr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "autofit")
    tblPr.append(layout)
    for r, row in enumerate(rows):
        for c, cell_text in enumerate(row):
            cell = table.cell(r, c)
            cell.paragraphs[0].text = ""
            para = cell.paragraphs[0]
            para.paragraph_format.space_before = Pt(2)
            para.paragraph_format.space_after = Pt(2)
            para.paragraph_format.line_spacing = 1.0
            add_rich(para, cell_text.strip(), size=9, citations=False)
            if r == 0:
                shade(cell, "1F3864")
                for run in para.runs:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            elif r % 2 == 0:
                shade(cell, "F4F7FB")
    tbl_borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "C9D2E3")
        tbl_borders.append(el)
    tblPr.append(tbl_borders)


def add_image(doc, path: Path, caption: str) -> None:
    mapped = FIG_MAP.get(path.name)
    if mapped:
        path = ROOT / mapped
    pic_para = doc.add_paragraph()
    pic_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_para.paragraph_format.space_before = Pt(6)
    pic_para.paragraph_format.space_after = Pt(2)
    pic_para.add_run().add_picture(str(path), width=Cm(14.2))
    pic_para.paragraph_format.keep_with_next = True
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    run = cap.add_run(caption)
    set_font(run, 9, color="595959")


def build() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines()

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
    set_font(normal, 10.5)
    normal.paragraph_format.line_spacing = 1.25
    normal.paragraph_format.space_after = Pt(6)

    for name, size, color in (("Heading 1", 15, "1F3864"),
                              ("Heading 2", 12.5, "2E5496"),
                              ("Heading 3", 11, "2E5496")):
        st = styles[name]
        set_font(st, size, bold=True, color=color)
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
                run = para.add_run("\n".join(code_lines))
                set_font(run, 9, mono=True)
            i += 1
            continue
        if in_code:
            code_lines.append(raw)
            i += 1
            continue

        if not line.strip():
            i += 1
            continue

        if line.startswith("# "):
            para = doc.add_paragraph(line[2:].strip(), style="Heading 1")
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if first_h1 else WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                set_font(run, 15, bold=True, color="1F3864")
            first_h1 = False
            i += 1
            continue
        if line.startswith("## "):
            para = doc.add_paragraph(line[3:].strip(), style="Heading 2")
            for run in para.runs:
                set_font(run, 12.5, bold=True, color="2E5496")
            pPr = para._p.get_or_add_pPr()
            pBdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "2")
            bottom.set(qn("w:color"), "2E5496")
            pBdr.append(bottom)
            pPr.append(pBdr)
            i += 1
            continue
        if line.startswith("### "):
            para = doc.add_paragraph(line[4:].strip(), style="Heading 3")
            for run in para.runs:
                set_font(run, 11, bold=True, color="2E5496")
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
            set_font(run, 9, color="595959")
            continue

        # 参考文献（悬挂缩进、小字号）
        if re.match(r"^\[\d+\]", line):
            para = doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0.7)
            para.paragraph_format.first_line_indent = Cm(-0.7)
            para.paragraph_format.space_after = Pt(1)
            para.paragraph_format.line_spacing = 0.9
            add_rich(para, line.strip(), size=7.6, citations=False)
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
                add_table(doc, rows)
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
        add_rich(para, " ".join(parts))
        i = j

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"written: {OUT}")


if __name__ == "__main__":
    build()
