"""生成《专家意见修订说明 v1.2》docx。

用法：
    python scripts/build_revision_docx.py
输出：
    C:\\Users\\弋昊阳\\OneDrive\\桌面\\低空航路项目-专家审核\\专家意见修订说明-v1.2.docx
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT_DIR = Path(r"C:\Users\弋昊阳\OneDrive\桌面\低空航路项目-专家审核")
OUT = OUT_DIR / "专家意见修订说明-v1.2.docx"
CN_FONT = "微软雅黑"
MONO_FONT = "Consolas"
DARK = RGBColor(0x1F, 0x38, 0x64)
MID = RGBColor(0x2E, 0x54, 0x96)
GREY = RGBColor(0x59, 0x59, 0x59)


def set_style_font(style, size=None, bold=None, color=None, name=CN_FONT):
    font = style.font
    font.name = name
    if size is not None:
        font.size = Pt(size)
    if bold is not None:
        font.bold = bold
    if color is not None:
        font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)


def shade(cell, hex_color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def fix_widths(table, widths_cm):
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    for row in table.rows:
        for idx, width in enumerate(widths_cm):
            row.cells[idx].width = Cm(width)
    for idx, width in enumerate(widths_cm):
        for cell in table.columns[idx].cells:
            cell.width = Cm(width)


def cell_text(cell, text, bold=False, size=9, align=None, color=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    if align is not None:
        p.alignment = align
    lines = str(text).split("\n")
    for i, line in enumerate(lines):
        if i:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(1)
            if align is not None:
                p.alignment = align
        run = p.add_run(line)
        run.bold = bold
        run.font.size = Pt(size)
        run.font.name = CN_FONT
        run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
        if color is not None:
            run.font.color.rgb = color


def add_table(doc, header, rows, widths, header_fill="DCE6F2", font_size=9):
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    tr_pr = hdr._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)
    for i, text in enumerate(header):
        cell_text(hdr.cells[i], text, bold=True, size=font_size,
                  align=WD_ALIGN_PARAGRAPH.CENTER)
        shade(hdr.cells[i], header_fill)
    for row_data in rows:
        row = table.add_row()
        tr_pr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        cant.set(qn("w:val"), "true")
        tr_pr.append(cant)
        for i, text in enumerate(row_data):
            cell_text(row.cells[i], text, size=font_size)
    fix_widths(table, widths)
    return table


def h(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.space_before = Pt(10 if level == 1 else 7)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    return p


def p(doc, text="", bold=False, size=10.5, color=None, space_after=3):
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(space_after)
    para.paragraph_format.line_spacing = 1.28
    run = para.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color is not None:
        run.font.color.rgb = color
    return para


def bullet(doc, text, size=10):
    para = doc.add_paragraph(style="List Bullet")
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(2)
    para.paragraph_format.line_spacing = 1.22
    run = para.add_run(text)
    run.font.size = Pt(size)
    return para


def mono(doc, text):
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(1)
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run(text)
    run.font.name = MONO_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), MONO_FONT)
    run.font.size = Pt(8.5)
    return para


def add_footer_page_number(section, prefix):
    p_footer = section.footer.paragraphs[0]
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p_footer.add_run(prefix + " · 第 ")
    run.font.size = Pt(8)
    run.font.color.rgb = GREY
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run2 = p_footer.add_run()
    run2.font.size = Pt(8)
    run2.font.color.rgb = GREY
    run2._r.append(fld_begin)
    run2._r.append(instr)
    run2._r.append(fld_end)
    run3 = p_footer.add_run(" 页")
    run3.font.size = Pt(8)
    run3.font.color.rgb = GREY


def build() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)
    sec.top_margin = Cm(1.8)
    sec.bottom_margin = Cm(1.6)
    add_footer_page_number(sec, "专家意见修订说明 v1.2")

    normal = doc.styles["Normal"]
    set_style_font(normal, size=10.5)
    normal.paragraph_format.line_spacing = 1.28
    set_style_font(doc.styles["Heading 1"], size=15, bold=True, color=DARK)
    set_style_font(doc.styles["Heading 2"], size=12, bold=True, color=MID)

    # 标题
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(18)
    title.paragraph_format.space_after = Pt(2)
    run = title.add_run("专家意见修订说明")
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = DARK

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(2)
    run = sub.add_run("v1.2 · 对应《低空航路规划原型-计划与Day1产出-审核稿 v1.1》")
    run.font.size = Pt(11.5)
    run.font.color.rgb = MID

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_after = Pt(14)
    run = meta.add_run("弋昊阳 | 2026-11-19 | 深圳中西部 25×19 km | 200 m 网格")
    run.font.size = Pt(9)
    run.font.color.rgb = GREY

    # 0 结论先行
    h(doc, "0. 结论先行", 1)
    p(doc, "专家意见共 18 条。我的处理是：14 条完全采纳、3 条部分采纳并写明理由、"
           "1 条（完整 SORA 定量审定）明确超出本项目范围、不假装能做。"
           "修订集中在四件事：")
    bullet(doc, "术语与定位：全部「风险」改为「人口暴露代理值」，明确不是 SORA、不是伤亡概率。")
    bullet(doc, "实验范围：核心实验从 5 组 OD × 3 层收窄为 1 组 OD × 60 m 单层；3 层与 5 OD 降为扩展。")
    bullet(doc, "约束实现：禁飞区从 1e6 惩罚改为删节点/删相交边 + 切角检查 + 独立几何验证。")
    bullet(doc, "评价口径：取消「暴露降 30%、距离增 ≤20%」的成功门槛，改为报告 Pareto 权衡与敏感性。")
    p(doc, "同步更新了 README、PLAN、docs/assumptions.md 与 docs/review_response.md；"
           "审核包新增「代码与过程记录」目录（代码快照、贡献台账、决策记录、验证日志）。",
      color=GREY, size=9.5)

    # 1 逐条处理
    h(doc, "1. 逐条处理", 1)
    rows = [
        ("1", "「风险」用词过强，应为人口暴露代理", "采纳", "README / 报告 / 图表统一改「暴露代理」；docs/assumptions.md §0"),
        ("2", "当前模型不能称为 SORA 评估", "采纳", "README 声明不做 SORA；assumptions §0 写清缺哪些要素"),
        ("3", "合成数据不能支撑深圳结论，删除「与深圳量级同阶」", "采纳", "README「数据」；assumptions §1 表格写明无现实对照"),
        ("4", "真实数据须给全名/年份/版本/许可/URL/处理步骤", "采纳", "assumptions §1 末段给出 WorldPop 引用模板与待办"),
        ("5", "高度因子 1.00/0.85/0.70 无依据", "采纳", "核心实验固定 60 m；90/120 仅 Day 11 情景，标注占位假设"),
        ("6", "层间 50 m 等效代价含义不清", "采纳", "不进核心实验；assumptions §6 说明只用于情景比较"),
        ("7", "1e6 惩罚不能保证 0 穿越", "采纳", "改为删禁飞节点/相交边；penalty 字段保留但注明弃用"),
        ("8", "对角边可能切角穿过禁飞区", "采纳", "对角边要求两正交邻格均可通行；输出用独立几何库验证"),
        ("9", "起终点吸附偏移未记录", "采纳", "结果表加 snap_offset_m（起/终），PLAN Day 2–4 落地"),
        ("10", "λ 需说明量纲；距离与暴露应分开报", "采纳", "λ 定义为无量纲偏好；报告长度与累积暴露两列，Pareto 非支配解"),
        ("11", "30% / 20% 成功门槛无依据", "采纳", "删除门槛，改为如实报告权衡；README 成功标准重写"),
        ("12", "首轮应收窄到 1 OD + 1 层", "采纳", "核心实验 1 组 OD（深圳北—深圳湾）× 60 m"),
        ("13", "每组 OD 需任务背景与坐标来源", "采纳", "configs/aoi.yaml 注释 + decisions.md 记录；PLAN Day 3 核对"),
        ("14", "Day 编号与日期不一致（11/17 vs 11/19）", "采纳", "PLAN v1.2：11/18 为评审/缓冲日不计入；D2=11/19…D21=12/08"),
        ("15", "contributions.md / decisions.md 未随包交付", "采纳", "审核包新增「代码与过程记录」，含两份文件副本"),
        ("16", "机场 5 km 圆只露弧线，正式报告需更大范围", "部分采纳", "审核稿保留（已注明圆心在 AOI 外）；Day 14 出宽幅空域图"),
        ("17", "9 页审核稿不适合作为最终作品集文档", "采纳", "审核稿定位为「计划/审阅稿」；最终 6–8 页报告另写（Day 15–16）"),
        ("18", "包内无代码，无法验证「新克隆可复现」", "采纳", "新增代码快照 zip + 验证日志（含 SHA256 比对）"),
    ]
    add_table(doc, ["#", "专家意见（摘要）", "处理", "落地位置"], rows,
              [0.9, 6.6, 1.5, 7.0], font_size=8.5)

    # 2 保留差异
    h(doc, "2. 三条保留差异（及理由）", 1)
    intro = p(doc, "以下三条没有完全照办，理由写在前面，便于专家判断是否接受：")
    intro.paragraph_format.keep_with_next = True
    rows2 = [
        ("3 层高度", "暂不作为核心实验", "换层需要可信的爬升/下降代价；目前没有依据。先做 60 m 单层，Day 11 只做情景敏感性，并明确标注假设。"),
        ("5 组 OD", "保留在 Day 10 批量扩展", "单组 OD 无法说明方法可推广；但必须先让 1 组 OD 的路线与验证完全可信，再扩展。"),
        ("合成数据", "短期保留用于 pipeline", "WorldPop 625 MB 当天无法下载。合成数据只验证流程与图表，所有涉及深圳的结论一律不写。"),
    ]
    add_table(doc, ["事项", "处理", "理由"], rows2, [2.6, 4.4, 9.0], font_size=9)

    # 3 计划变化
    h(doc, "3. 修订前后对比", 1)
    rows3 = [
        ("核心实验", "5 组 OD × 3 层 × 3 种缓冲", "1 组 OD × 60 m 单层；3 层/5 OD 后移"),
        ("禁飞区约束", "大惩罚值 1e6", "删节点/边 + 切角检查 + 独立几何验证"),
        ("成功标准", "暴露降 ≥30%、距离增 ≤20%", "Pareto 权衡 + 敏感性 + 如实报告"),
        ("术语", "风险 / 风险面", "人口暴露代理值 / 暴露面"),
        ("路线验证", "只看代价是否绕开", "独立几何库相交检查，0 穿越为硬验收"),
        ("起终点", "直接吸附，不记录", "记录 snap_offset_m，>100 m 人工复核"),
        ("日期", "D1 11/17、D2 11/19 但称连续 21 天", "11/18 评审日不计入；21 个执行日到 12/08"),
        ("交付物", "报告/图/视频", "加代码快照、贡献台账、决策记录、验证日志"),
    ]
    add_table(doc, ["项目", "修订前", "修订后"], rows3, [2.8, 6.4, 6.8], font_size=9)

    # 4 证据状态
    h(doc, "4. 当前证据状态", 1)
    rows4 = [
        ("Day 1 统计数字", "已验证", "独立脚本从 CSV 复算：总人口 5,124,820.8、p95 1,794.284、最大格 4,470.6、非零 12,197"),
        ("源栅格一致性", "已验证", "聚合总和 5,124,821 vs 源 5,136,125，差 0.22%（边缘无数据格）"),
        ("环境与依赖", "已验证", "pip check 通过；numpy 2.2.6 / pandas 3.1.1 / rasterio 1.5.2 / networkx 3.7"),
        ("新克隆复现", "已验证", "安装 131.8 s + 运行 14.9 s；CSV/PNG SHA256 与本地一致"),
        ("路线/禁飞/λ/Pareto", "未实现", "Day 2–5 实现；在此之前不写任何路线结论"),
        ("真实 WorldPop", "未接入", "Day 8 前尝试；接不上则报告只写合成数据流程验证"),
        ("文献依据", "未系统整理", "Day 8 补 SORA 2.5、CAAC 条例、低空风险评估文献"),
    ]
    add_table(doc, ["项目", "状态", "说明"], rows4, [3.6, 2.2, 10.2], font_size=8.8)

    # 5 下一步
    h(doc, "5. 下一步（Day 2–7）", 1)
    bullet(doc, "Day 2（11/19）：200 m 网格 + 禁飞硬掩膜（删节点/边、切角检查、吸附偏移），出网格图与掩膜测试。", 9.5)
    bullet(doc, "Day 3（11/20）：核心 OD 建图 + 最短路 baseline，核对起终点坐标并记录 snap_offset_m。", 9.5)
    bullet(doc, "Day 4（11/21）：λ=1 暴露加权路 + 独立几何验证，输出 baseline vs 加权对比表。", 9.5)
    bullet(doc, "Day 5（11/22）：λ 0–2 扫描 + Pareto（单层 60 m）。", 9.5)
    bullet(doc, "Day 6（11/23）：网格分辨率 100/200/400 m 敏感性。", 9.5)
    bullet(doc, "Day 7（11/24）：周复盘、README v0.1、push。", 9.5)

    # 6 附件
    h(doc, "6. 本包内文件", 1)
    rows6 = [
        ("专家意见修订说明-v1.2.docx / .pdf", "本文"),
        ("低空航路规划原型-计划与Day1产出-审核稿 v1.1", "原审核稿（历史记录；与本文冲突处以本文与 README/PLAN 为准）"),
        ("00_先看这里.txt", "3 分钟阅读顺序"),
        ("原始文档/", "README、PLAN v1.2、spec、assumptions v0.2、aoi.yaml"),
        ("代码与过程记录/", "代码快照 zip、contributions.md、decisions.md、验证日志"),
        ("figures/、数据/", "人口热力图、网格人口 CSV"),
    ]
    add_table(doc, ["文件", "作用"], rows6, [7.0, 9.0], font_size=9)

    p(doc, "声明：本项目为方法演示与能力证明，所有禁飞区、人口数据均为示意或合成，"
           "不构成适航审定、运行许可或任何实际飞行依据。", size=8.5, color=GREY, space_after=0)

    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"written: {path}")
