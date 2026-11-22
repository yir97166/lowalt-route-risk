"""生成《第一周复盘（Day 1–8）》Word 文档，供专业人士审阅。

输出：C:\\Users\\弋昊阳\\OneDrive\\桌面\\low-attitude report\\02_专家审核\\
      20261122_第一周复盘_周报.docx（覆盖 20261120 旧版）
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

OUT_DIR = Path(r"C:\Users\弋昊阳\OneDrive\桌面\low-attitude report\02_专家审核")
OUT = OUT_DIR / "20261122_第一周复盘_周报.docx"

CN_FONT = "微软雅黑"
DARK = RGBColor(0x1F, 0x38, 0x64)
MID = RGBColor(0x2E, 0x54, 0x96)


# ---------- 基础样式 ----------
def set_style_font(style, size, bold=False, color=None):
    style.font.name = CN_FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    style.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)


def setup(doc: Document) -> None:
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)
    sec.top_margin = Cm(1.8)
    sec.bottom_margin = Cm(1.8)

    normal = doc.styles["Normal"]
    set_style_font(normal, 10.5)
    normal.paragraph_format.space_after = Pt(2.5)
    normal.paragraph_format.line_spacing = 1.25

    for name, size in (("Heading 1", 14.5), ("Heading 2", 11.5), ("Title", 22)):
        st = doc.styles[name]
        set_style_font(st, size, bold=True, color=DARK if size != 11.5 else MID)
        st.paragraph_format.space_before = Pt(12 if size > 12 else 8)
        st.paragraph_format.space_after = Pt(4)


def shade(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def table(doc: Document, header: list[str], rows: list[list[str]], widths=None) -> None:
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0]
    for i, text in enumerate(header):
        cell = hdr.cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(text)
        run.font.name = CN_FONT
        run.font.size = Pt(9.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
        shade(cell, "1F3864")
    trPr = hdr._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    trPr.append(tblHeader)
    for row_data in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row_data):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(text))
            run.font.name = CN_FONT
            run.font.size = Pt(9.5)
            run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
    if widths:
        t.autofit = False
        tblPr = t._tbl.tblPr
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tblPr.append(layout)
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)


def h(doc: Document, text: str, level: int = 1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.keep_with_next = True
    return p


def p(doc: Document, text: str, bold: bool = False, size: float = 10.5):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.name = CN_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
    return para


def mono(doc: Document, text: str):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    return para


def bullet(doc: Document, text: str):
    para = doc.add_paragraph(style="List Bullet")
    run = para.add_run(text)
    run.font.name = CN_FONT
    run.font.size = Pt(10.5)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
    return para


def footer_page_number(doc: Document) -> None:
    footer = doc.sections[0].footer
    para = footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run("低空航路规划原型 · 第一周复盘（Day 1–8）· 第 ")
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    run.font.name = CN_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "17")
    rPr.append(sz)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    para._p.append(fld)

    run2 = para.add_run(" 页")
    run2.font.size = Pt(8.5)
    run2.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    run2.font.name = CN_FONT
    run2._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)


# ---------- 内容 ----------
def build() -> Document:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    setup(doc)
    footer_page_number(doc)

    # 封面
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title.add_run("低空航路规划原型")
    tr.font.name = CN_FONT
    tr.font.size = Pt(24)
    tr.font.bold = True
    tr.font.color.rgb = DARK
    tr._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sub.add_run("第一周复盘（Day 1–8）· 供专业人士审阅")
    sr.font.name = CN_FONT
    sr.font.size = Pt(13)
    sr.font.color.rgb = MID
    sr._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    mr = meta.add_run(
        "弋昊阳 ｜ 2026-11-17 至 11-21 ｜ 深圳中西部 25×19 km ｜ "
        "200 m 网格 ｜ 60 m 单层核心实验 ｜ 8 个工作日"
    )
    mr.font.name = CN_FONT
    mr.font.size = Pt(9.5)
    mr.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    mr._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    # 0 摘要
    h(doc, "0. 一页摘要")
    p(doc, "本周把「数据 → 网格 → 空域约束 → 最短路 → 暴露加权 → λ 扫描与分辨率敏感性"
           " → 文献与参数敏感性 → 一键复现」这条链路完整跑通，并全部留下可复现证据。"
           "核心实验按专家意见收窄为 1 组 OD（深圳北—深圳湾）× 1 层（60 m），"
           "其余 4 组 OD 只作扩展参考。")
    bullet(doc, "核心 OD：14.665 km，绕行率 1.087，等效暴露长度 C 2,840.3 代理·米（λ=0）"
                "→ 2,727.0（λ=1，平均暴露强度 E 0.1937 → 0.1860），长度不变、C −4.0%；"
                "5 组 OD 全部可达、0 次穿越硬禁飞区。")
    bullet(doc, "λ 扫描（0–2，105 条路线）：λ≈1.3 是分界。λ≥1.3 才出现真绕行——"
                "多走 3.2% 距离，换 17.0% 暴露下降；λ 再大也不再变化（只有 3 个不同解）。")
    bullet(doc, "分辨率敏感性：100 / 200 / 400 m 下，沿路平均人口密度下降 2.6% / 4.0% / 4.3%，"
                "结论方向一致；主实验保留 200 m（公开人口数据 100 m 与计算量折中，"
                "400 m 起点吸附偏移 158.6 m 需在报告标注）。")
    bullet(doc, "遮蔽系数敏感性：s=0.2/0.3/0.4 的路线切换阈值实测 1.125 / 1.275 / 1.500，"
                "与 1/(1−s) 预测一致；三组路线集合相同，遮蔽只平移阈值、不改变结论。")
    bullet(doc, "文献收口：11 条可核对文献（含 SORA 2.5 原文、地面风险与人口数据论文）；"
                "SORA 把「遮蔽」列为缓解措施 M1，不是固定系数——我们的 0.30 只能算工程假设。")
    bullet(doc, "工程质量：pytest 20 项通过；`scripts/run_all.py` 8 步 63.4 s 全过；"
                "仓库已推到 GitHub（公开），全新克隆安装 131.8 s、两个脚本 14.9 s，"
                "输出 CSV/PNG 与本地逐字节一致（SHA256）。")

    # 1 进度
    h(doc, "1. 本周进度与计划对照")
    table(
        doc,
        ["天", "日期", "计划任务", "实际完成", "证据"],
        [
            ["Day 1", "11/17", "环境、数据、第一张图", "合成人口栅格 + 128×98 网格 + 人口暴露热力图", "figures/00_population.png"],
            ["Day 2", "11/19", "网格 + 禁飞硬掩膜", "硬禁飞 276 格；官方净空走廊 4,706 格（受控）；切角规则、吸附、几何校验", "figures/01_grid_nofly.png"],
            ["Day 3", "11/19", "建图 + 最短路 baseline", "12,268 节点 / 48,251 边；5 组 OD 最短路线，0 穿越", "figures/02_shortest_path.png；results/baseline.csv"],
            ["Day 4", "11/20", "暴露加权 vs baseline", "λ=1 对比：5 组 OD 长度 0% 变化，暴露 −1.4%～−14.2%（等长 tie-break）", "figures/03_route_compare.png；results/compare.csv"],
            ["Day 5", "11/20", "λ 扫描 + Pareto", "105 条路线；核心 OD 只有 3 个不同解，阈值 λ≈1.3", "figures/05_pareto.png；results/pareto.csv"],
            ["Day 6", "11/20", "网格分辨率敏感性", "100/200/400 m 对比；密度下降 2.6%/4.0%/4.3%", "figures/06_resolution.png；results/resolution.csv"],
            ["Day 7", "11/21", "周复盘 + README v0.1", "一键 8 步 63.4 s；README v0.1；仓库公开推送成功", "scripts/run_all.py；README.md；GitHub"],
            ["Day 8", "11/21", "文献 + 遮蔽参数敏感性", "11 条文献（含 SORA 2.5）；阈值 1.125/1.275/1.500，路线集合不变", "docs/literature.md；figures/07_param_sensitivity.png"],
        ],
        widths=[1.6, 1.5, 3.2, 6.6, 4.1],
    )
    p(doc, "说明：11/18 为专家意见评审日，不计入 21 个执行日；Day 5–8 合并/提前到 11/20–11/21 完成。",
      size=9)

    # 2 结果
    h(doc, "2. 主要结果")

    h(doc, "2.1 网格与空域约束", 2)
    p(doc, "AOI 切分为 128 列 × 98 行 = 12,544 个 200 m 格（EPSG:32649）。"
           "硬禁飞区按「格与区有任何重叠即阻挡」处理，共 276 格（2.20%）：梧桐山 144 格、"
           "深圳水库 132 格。机场净空保护区按深公规〔2017〕3 号（跑道中心线两侧各 10 km、"
           "端外 20 km）建走廊，覆盖 4,706 格（37.52%），标为「受控/需审批」而非硬禁飞——"
           "因为它不是无人机禁飞区，且核心 OD 终点落在其中。")
    bullet(doc, "起终点吸附：核心 OD 起点偏移 66.5 m、终点 91.3 m；南山—宝安起点 107.7 m 超 100 m 阈值，"
                "用户 2026-11-19 确认「先这样」，报告中如实标注。")
    bullet(doc, "切角规则：对角移动要求两个正交邻格都畅通，避免「贴着禁飞区角切过去」。")

    h(doc, "2.2 最短路 baseline（λ=0，5 组 OD）", 2)
    table(
        doc,
        ["OD", "长度 km", "绕行率", "净空区内格数", "硬禁飞穿越"],
        [
            ["深圳北—深圳湾（核心）", "14.665", "1.087", "8 / 59（13.6%）", "0"],
            ["福田 CBD—宝安机场东", "21.885", "1.078", "39 / 98（34.7%）", "0"],
            ["南山—宝安", "8.554", "1.037", "33 / 33（100%）", "0"],
            ["罗湖—福田", "7.014", "1.051", "0 / 34（0%）", "0"],
            ["宝安中心—南山", "8.574", "1.076", "36 / 36（100%）", "0"],
        ],
        widths=[5.6, 2.4, 2.2, 4.2, 3.0],
    )

    h(doc, "2.3 λ=1 暴露加权 vs baseline", 2)
    p(doc, "5 组 OD 的长度变化全部为 0.00%。原因是 8 邻接网格存在大量等长路径，"
           "λ=1 只在等长解里挑累计暴露更低的一条（tie-break），不是真正的绕路。"
           "这一点必须如实写进报告，不能表述为「牺牲距离换安全」。")
    table(
        doc,
        ["OD", "长度变化", "C λ=0（代理·米）", "C λ=1（代理·米）", "C 变化"],
        [
            ["深圳北—深圳湾（核心）", "0.00%", "2,840.3", "2,727.0", "−4.0%"],
            ["福田 CBD—宝安机场东", "0.00%", "3,376.5", "2,898.5", "−14.2%"],
            ["南山—宝安", "0.00%", "2,645.7", "2,471.9", "−6.6%"],
            ["罗湖—福田", "0.00%", "4,387.8", "4,326.0", "−1.4%"],
            ["宝安中心—南山", "0.00%", "4,993.6", "4,594.0", "−8.0%"],
        ],
        widths=[5.6, 2.6, 3.4, 3.4, 2.4],
    )
    p(doc, "C 是「等效暴露长度」，定义 C = Σ(边长 × 边暴露强度)，单位「代理·米」（proxy·m），"
           "可读作「假设全程以暴露强度 1.0 飞行，相当于飞了多少米」，恒有 C ≤ L；"
           "它与路线长度不可互换，也不是伤亡人数。平均暴露强度 E = C / L（无量纲），"
           "本次 E 由 0.1937 降到 0.1860。完整定义见仓库 docs/indicator_definition.md。", size=9)

    h(doc, "2.4 λ 扫描与 Pareto（核心 OD）", 2)
    table(
        doc,
        ["λ 区间", "长度 km", "C（代理·米）", "E = C/L", "解释"],
        [
            ["0（baseline）", "14.665", "2,840.3", "0.1937", "纯最短路"],
            ["0.025–1.25", "14.665", "2,727.0", "0.1860", "长度不变，等长解里挑低暴露（tie-break）"],
            ["1.275–2.0", "15.134", "2,357.5", "0.1558", "真绕行：+3.2% 距离，C −17.0%"],
        ],
        widths=[3.6, 2.6, 3.2, 2.4, 8.4],
    )
    p(doc, "去重规则：同一 OD 下格心序列逐格相同的算同一个解，等长但序列不同的算两个解"
           "（results/pareto_routes.csv 给了每条解的 hash）。核心 OD 81 档 λ 只有这 3 个解，"
           "切换点在 λ≈0.025（等长 tie-break）与 λ≈1.275（真绕行）；"
           "明细与读法见仓库 docs/pareto_reading.md、figures/09_pareto_routes.png。", size=9)
    p(doc, "其余 4 组 OD 在 λ=2 时（相对 λ=0）：福田 0% / −14.2%；南山 +4.1% / −13.8%；"
           "罗湖 +30.3% / −40.5%；宝安中心 +27.2% / −37.7%。人口越密、越值得绕。")

    h(doc, "2.5 网格分辨率敏感性（核心 OD）", 2)
    table(
        doc,
        ["网格", "节点数", "长度 km", "绕行率", "沿路密度 λ=0→λ=1（人/km²）", "耗时"],
        [
            ["100 m", "48,464", "14.548", "1.077", "12,491 → 12,160（−2.6%）", "2.5 s"],
            ["200 m（主）", "12,268", "14.665", "1.087", "12,838 → 12,324（−4.0%）", "0.7 s"],
            ["400 m", "3,109", "14.817", "1.108", "11,855 → 11,340（−4.3%）", "0.2 s"],
        ],
        widths=[3.0, 2.6, 2.6, 2.4, 6.6, 1.8],
    )
    p(doc, "跨分辨率不能直接比 C（随格面积与离散化一起变），所以同时报「沿路平均人口密度」与 E。"
           "400 m 起点吸附偏移 158.6 m，超过 100 m 阈值，报告中需标注。", size=9)
    p(doc, "补充实验（审核后，scripts/make_origin_shift.py）：把核心 OD 两端整体平移 ±0.5 格共 9 个位置，"
           "看结果对吸附位置的敏感性——100 m 网格 λ=0 长度 ±0.80%、C ±3.26%；200 m 为 ±1.36% / ±6.56%；"
           "400 m 为 ±2.70% / +20.4%。即 400 m 下「吸附位置」本身就能让 C 变动两成，"
           "与 λ 带来的 17% 差异同量级，所以 400 m 只能当稳健性对照、不能当主结论，"
           "主实验维持 200 m（λ=1 长度 ±3.76%、C −17.9%），并把该区间写成「±」而不是单点值。"
           "详见图 figures/08_origin_shift.png 与 results/origin_shift_summary.csv。", size=9)

    h(doc, "2.6 遮蔽系数敏感性与 SORA 对照（核心 OD，60 m）", 2)
    p(doc, "遮蔽系数 s 没有可引文献，因此不假设它是「真值」，而是看它把结论改变多少："
           "固定 s，扫描 λ=0–2（步长 0.025），找路线第一次切换的阈值。")
    table(
        doc,
        ["遮蔽系数 s", "实测切换阈值 λ", "1/(1−s) 预测", "不同路线数"],
        [
            ["0.2", "1.125", "1.116", "3"],
            ["0.3（主）", "1.275", "1.275", "3"],
            ["0.4", "1.500", "1.487", "3"],
        ],
        widths=[3.6, 4.4, 4.2, 3.0],
    )
    bullet(doc, "三组路线集合完全相同，只是阈值平移：遮蔽系数改变「何时开始绕」，"
                "不改变「绕与不绕」两种解的存在性。")
    bullet(doc, "SORA 2.5 原文核对：目标地面风险 1E-6 致死/小时；iGRC 由最大人口密度分档"
                "（<25 到 >250000 人/km²）与无人机尺寸/速度决定；评估范围为运行体积 + 地面风险缓冲。"
                "「遮蔽」在 SORA 中是缓解措施 M1(A)，不是固定乘数。")
    bullet(doc, "因此本项目只把 0.30 当作工程假设，并在报告里写明：换成 0.2 或 0.4，"
                "结论方向不变、阈值移动；不宣称 0.30 是标准值。")

    # 3 决策
    h(doc, "3. 本周关键决策与依据（摘要）")
    table(
        doc,
        ["#", "决策", "依据 / 理由"],
        [
            ["1", "术语用「人口暴露代理」，不叫风险/安全", "模型不含失效概率与伤亡换算，专家意见第 1 条"],
            ["2", "核心实验 1 OD × 60 m 单层；3 层、5 OD 降为情景与扩展", "换层代价无依据；先把单层做可信"],
            ["3", "禁飞区删节点/删边 + 切角规则，不再用 1e6 惩罚", "惩罚不能保证 0 穿越；独立几何库复核"],
            ["4", "净空保护区标「受控/需审批」，不当硬禁飞", "深公规〔2017〕3 号是净空保护区，不是无人机禁飞区"],
            ["5", "C = Σ(边长×边暴露强度)，单位「代理·米」，另报 E = C/L；不报绝对伤害", "每公里失效概率近似相同时，期望伤害 ∝ C；但仍只做相对比较"],
            ["6", "边权 = 长度 ×(1+λ×暴露)，λ 无量纲", "便于解释与扫描；长度、暴露分两列报告"],
            ["7", "主网格 200 m；100/400 m 只做敏感性", "公开人口数据 100 m 与计算量折中"],
            ["8", "λ≈1.3 作为权衡阈值，但不宣称最优 λ", "105 条路线里只有 3 个不同解，阈值是观察结果"],
            ["9", "OD 坐标为手工近似，逐个报告吸附偏移", "无门牌级权威坐标；不编造精度"],
            ["10", "合成人口数据只验证流程，不写深圳结论", "WorldPop 625 MB 当日无法稳定下载"],
            ["11", "文献引用必须可核对（DOI/文号/原文页），不引二手转述", "专家要求数据与依据可追溯；11 条全部核对过"],
            ["12", "遮蔽系数 0.30 只作工程假设，另做 0.2/0.3/0.4 敏感性", "SORA 中遮蔽是缓解措施 M1，不是固定系数"],
            ["13", "仓库公开、README v0.1、一键 8 步脚本", "新克隆 10 分钟内跑通是验收标准之一"],
        ],
        widths=[1.0, 7.6, 8.4],
    )
    p(doc, "完整 17 条决策与日期见仓库 docs/decisions.md；假设与不适用范围见 docs/assumptions.md。", size=9)

    # 4 证据
    h(doc, "4. 证据与可复现")
    table(
        doc,
        ["项目", "结果"],
        [
            ["提交记录", "28 个提交，从 2b266ed（Day 1）到 7de4105（Day 8）；main 与 origin/main 一致"],
            ["测试", "pytest 26 项通过：mask 9、graph 5、router 6、metrics 6"],
            ["一键复现", "scripts/run_all.py 8 步全过，实测 63.4 s"],
            ["公开仓库", "https://github.com/yir97166/lowalt-route-risk（Public，SSH over 443）"],
            ["全新克隆", "安装 131.8 s + 两个脚本 14.9 s，退出码 0，pip check 干净"],
            ["逐字节复现", "grid_population.csv 与 00_population.png 的 SHA256 与本地一致"],
            ["独立复核", "每条路线用 shapely 独立校验：相邻步长、硬禁飞格、逐段相交、最小间距"],
            ["人工抽查", "用户 2026-11-20 在 Excel 核对 λ=1：14.665 km / 2.727；11-20 确认 Pareto 拐点在右侧 (3.2%, 17%)"],
        ],
        widths=[3.4, 13.4],
    )

    # 5 局限
    h(doc, "5. 局限、风险与未验证项")
    table(
        doc,
        ["局限", "影响", "处理"],
        [
            ["人口为合成数据", "所有绝对数字不代表深圳真实情况", "只验证方法；报告显著标注"],
            ["净空区≠禁飞区", "不能据此判断合法/非法", "标「受控/需审批」，不下合规结论"],
            ["核心实验仅 60 m 单层", "无法回答高度权衡", "3 层只作 Day 11 情景，标注假设"],
            ["λ=1 长度零变化", "易被误读成「无代价降暴露」", "明确是等长 tie-break；真绕行在 λ≥1.3"],
            ["400 m 起点偏移 158.6 m", "粗网格代表性下降", "报告标注，主实验用 200 m"],
            ["通信/电磁干扰未建模", "真实运行的重要风险缺失", "写入局限；有频谱数据可作第二层"],
            ["失效概率、坠落轨迹未知", "不能换算伤亡", "只做相对比较，不报绝对风险"],
            ["未按 SORA 做定量评估", "不能声称符合 SORA；iGRC 分档与连续暴露未映射", "只把 SORA 当参照，报告写明「非审定/非合规」"],
            ["遮蔽 0.30 无实测依据", "换系数会移动阈值", "已做 0.2/0.3/0.4 敏感性；结论方向不变"],
        ],
        widths=[4.4, 6.2, 6.2],
    )

    # 6 下周
    h(doc, "6. 下阶段计划（Day 9–13）")
    table(
        doc,
        ["天", "任务", "产出 / 验收"],
        [
            ["Day 9", "单元测试补全（风险/图/掩膜/路线）", "pytest 覆盖 4 类核心逻辑"],
            ["Day 10", "5 组 OD 批量实验", "results/od_summary.csv；无缺失"],
            ["Day 11", "高度层与缓冲情景敏感性", "情景表 + 图；明确哪些是假设"],
            ["Day 12", "CLI、配置与代码整理", "一条命令复现全部结果"],
            ["Day 13", "随机种子、日志、异常处理", "同种子结果一致；错误可定位"],
        ],
        widths=[1.6, 9.0, 6.2],
    )

    # 7 问题
    h(doc, "7. 请专业人士重点看的 6 个问题")
    for q in [
        "Q1 用「人口暴露代理 + 累计暴露」做路线比较，在学术上是否有更标准的指标或必须补的项？",
        "Q2 λ=1 只产生等长 tie-break、λ≥1.3 才真绕行——这个「阈值」结论在方法上站得住吗？还是网格对称性造成的假象？",
        "Q3 机场净空保护区按「受控/需审批」处理、不做硬禁飞，这个边界是否可接受？",
        "Q4 遮蔽 0.30 只是工程假设（SORA 里遮蔽属于缓解措施 M1，不是固定乘数）。"
        "在不能拿到实测数据时，是把 0.30 写死并做敏感性，还是干脆去掉遮蔽？",
        "Q5 我们不按 SORA 做定量评估（iGRC 分档 vs 连续暴露未映射），只当参照。"
        "这个边界在硕士申请作品里是否够诚实、够用？",
        "Q6 通信/电磁干扰没有数据就不建模、只写局限，这样的处理在审稿/答辩中是否足够？",
    ]:
        para = p(doc, q)
        para.paragraph_format.space_before = Pt(6)
        ans = p(doc, "专家意见：", size=9.5)
        ans.paragraph_format.space_after = Pt(10)

    # 8 附件
    h(doc, "8. 附件与路径")
    p(doc, "公开仓库：https://github.com/yir97166/lowalt-route-risk")
    p(doc, "项目根目录：C:\\Users\\弋昊阳\\OneDrive\\文档\\deepseek-harness\\default-workspace\\lowalt-route-risk")
    p(doc, "本周资料夹：C:\\Users\\弋昊阳\\OneDrive\\桌面\\low-attitude report\\")
    p(doc, "包内材料：01_原始资料\\（机场通告与 4 张航图 6A-1、6A-2、2A-1、2P-1）；"
           "02_专家审核\\（专家意见、审核包 v1.2、本周报）；03_图与结果_20261122\\"
           "（05_pareto.png、06_resolution.png、核心 OD λ 扫描表）；仓库 docs\\literature.md"
           "（11 条文献）、docs\\decisions.md（17 条决策）、figures\\07_param_sensitivity.png、"
           "results\\param_sensitivity*.csv。", size=9.5)
    p(doc, "复现（PowerShell，仓库根目录）：", size=9.5)
    mono(doc, ".\\venv\\Scripts\\python.exe scripts\\run_all.py   # 8 步，约 63 s")
    mono(doc, ".\\venv\\Scripts\\python.exe -m pytest -q      # 26 passed")
    p(doc, "验收口径：一键脚本从零全过、测试全绿、CSV/PNG 由脚本重新生成；"
           "所有数字以仓库 results/ 与 figures/ 为准，本报告不手改数字。", size=9)
    p(doc, "免责声明：本项目为方法演示与能力证明，人口数据为合成、禁飞区为示意或公开资料近似，"
           "不构成适航审定、运行许可、合规判断或任何实际飞行依据。", size=9)

    doc.save(OUT)
    print(f"written: {OUT}")
    return doc


if __name__ == "__main__":
    build()
