"""生成《第一周复盘（Day 1–9）》Word 文档，供专业人士审阅。

输出：C:\\Users\\弋昊阳\\OneDrive\\桌面\\low-altitude report\\02_专家审核\\
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

OUT_DIR = Path(r"C:\Users\弋昊阳\OneDrive\桌面\low-altitude report\02_专家审核")
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
    sec.top_margin = Cm(1.5)
    sec.bottom_margin = Cm(1.5)

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
    run = para.add_run("低空航路规划原型 · 阶段复盘（Day 1–15）· 第 ")
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
    sr = sub.add_run("阶段复盘（Day 1–15）· 供专业人士审阅")
    sr.font.name = CN_FONT
    sr.font.size = Pt(13)
    sr.font.color.rgb = MID
    sr._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    mr = meta.add_run(
        "弋昊阳 ｜ 2026-11-17 至 11-24 ｜ 深圳中西部 25×19 km ｜ "
        "200 m 网格 ｜ 60 m 单层核心实验 ｜ 15 个执行日"
    )
    mr.font.name = CN_FONT
    mr.font.size = Pt(9.5)
    mr.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    mr._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    # 0 摘要
    h(doc, "0. 一页摘要")
    p(doc, "本周把「数据 → 网格 → 空域约束 → 最短路 → 暴露加权 → λ 扫描与分辨率敏感性"
           " → 文献与参数敏感性 → 一键复现 → 测试补全 → 真实数据切换」这条链路完整跑通，并全部留下可复现证据。"
           "核心实验按专家意见收窄为 1 组 OD（罗湖—福田）× 1 层（60 m）；Day 14 起主人口数据切为 WorldPop 2020。")
    bullet(doc, "核心 OD：7.014 km，绕行率 1.051，等效暴露长度 C 3,922.2 代理·米（λ=0）"
                "→ 2,625.9（λ=1，平均暴露强度 E 0.5592 → 0.3496），长度 +7.09%、C −33.05%；"
                "0 次穿越硬禁飞区。")
    bullet(doc, "机场净空保护区按深公规〔2017〕3 号「严禁」原文改作硬禁飞：硬禁飞 4,982 格（39.7%）；"
                "机场周边 4 组 OD 端点落在走廊内，判不可达——这本身是结论：起降点不宜设在净空保护区内。")
    bullet(doc, "λ 扫描（0–2，步长 0.025；81 档）：核心 OD 只有 3 个不同解、2 个切换点；"
                "λ≈0.025 起先等长 tie-break，λ≈0.825 起才真绕行——多走 7.09% 距离，换 C −33.05%（相对 λ=0）。")
    bullet(doc, "分辨率敏感性：100 / 200 / 400 m 下，长度 +5.8% / +7.1% / 0.0%，沿路平均人口密度 −40.8% / −38.8% / −12.6%；"
                "主实验保留 200 m，400 m 两端吸附偏移 229/141 m，只作稳健性对照。")
    bullet(doc, "遮蔽系数敏感性：s=0.2/0.3/0.4 的路线切换阈值实测 0.725 / 0.825 / 0.950，"
                "与 1/(1−s) 预测一致；三组解数都是 3，遮蔽只平移阈值、不改变结论。")
    bullet(doc, "文献收口：11 条可核对文献（含 SORA 2.5 原文、地面风险与人口数据论文）；"
                "SORA 把「遮蔽」列为缓解措施 M1，不是固定系数——我们的 0.30 只能算工程假设。")
    bullet(doc, "工程质量：pytest 62 项通过；`scripts/run_all.py` 13 步 117.2 s 全过；"
                "仓库已推到 GitHub（公开），全新克隆安装与输出哈希均可复核。")

    bullet(doc, "Day 10 批量（5 组走廊外 OD）：3 组 λ=1 出现真绕行；龙华—福田最明显——多走 8.51% 距离，"
                "换 C −35.38%；北站、布吉只发生等长 tie-break；机场向 4 组仍判不可达。")
    bullet(doc, "Day 11 情景：高度只把 λ 阈值按 1/f 平移（0.825 → 0.950 → 1.175），路线几何不变，"
                "不能据此说「越高越安全」；安全区尺寸 ×0.5/×1.0/×1.5 只影响机场向 OD，核心 OD 恒为 7.014 km。")
    bullet(doc, "Day 14 真实数据：主人口数据切 WorldPop 2020（625 MB），13 步 117.2 s；"
                "最明显变化是 λ=1 从「零距离代价 tie-break」变成真绕行（+497 m，C −33%）。")
    bullet(doc, "Day 15 图定稿：3 张核心图统一 300 dpi；新增宽幅空域图 13_airspace_wide.png，"
                "用米制坐标完整显示 40×20 km 净空走廊与 AOI 的重叠关系。")
    # 1 进度
    h(doc, "1. 本周进度与计划对照")
    table(
        doc,
        ["天", "日期", "计划任务", "实际完成", "证据"],
        [
            ["Day 1", "11/17", "环境、数据、第一张图", "合成人口栅格跑通流程；128×98 网格；人口暴露热力图", "figures/00_population.png"],
            ["Day 2", "11/19", "网格 + 禁飞硬掩膜", "净空走廊按官方尺寸建、改硬禁飞；硬禁飞 4,982 格；切角/吸附/几何校验", "figures/01_grid_nofly.png"],
            ["Day 3", "11/19", "建图 + 最短路 baseline", "核心 OD 建图（7,562 节点 / 29,496 边）；罗湖—福田 7.014 km，0 穿越", "figures/02_shortest_path.png；results/baseline.csv"],
            ["Day 4", "11/20", "暴露加权 vs baseline", "λ=1 对比流程与指标表（真实数据结果见 §2.3）", "figures/03_route_compare.png；results/compare.csv"],
            ["Day 5", "11/20", "λ 扫描 + Pareto", "λ 0.025 步长扫描、去重、Pareto 图（见 §2.4）", "figures/05_pareto.png；results/pareto.csv"],
            ["Day 6", "11/20", "网格分辨率敏感性", "100/200/400 m 重建网格与对照（见 §2.5）", "figures/06_resolution.png；results/resolution.csv"],
            ["Day 7", "11/21", "周复盘 + README v0.1", "一键脚本（现 13 步）；README v0.1；仓库公开推送成功", "scripts/run_all.py；README.md；GitHub"],
            ["Day 8", "11/21", "文献 + 遮蔽参数敏感性", "11 条文献（含 SORA 2.5）；遮蔽敏感性（见 §2.6）", "docs/literature.md；figures/07_param_sensitivity.png"],
            ["Day 9", "11/22", "测试补全（风险/图/掩膜/路线）", "pytest 45→52（Day 14 后 62 项）", "tests/；pytest -q"],
            ["Day 10", "11/22（提前）", "5 组走廊外 OD 批量实验", "5 组全部可达；批量结果见 §2.7", "figures/10_batch_od.png；results/od_summary.csv"],
            ["Day 11", "11/23（提前）", "高度层与安全区尺寸情景", "高度阈值 0.825/0.950/1.175；安全区 ×0.5/1.0/1.5 覆盖 9.3%/39.7%/60.7%", "figures/11_altitude_scenario.png；12_safety_area_scenario.png"],
            ["Day 12", "11/23（提前）", "CLI、配置与代码整理", "`python -m src.cli all` 一条命令复现；CLI 6 项测试", "src/cli.py；tests/test_cli.py"],
            ["Day 13", "11/23（提前）", "随机种子、日志、异常处理", "logs/ 逐步 JSON；种子进 config；失败即停", "src/runlog.py；logs/latest.json"],
            ["Day 14", "11/23", "主人口数据切真实 WorldPop", "625 MB 栅格校验通过；13 步 117.2 s；λ=1 真绕行 +7.09%/−33.05%", "data/raw/worldpop/；results/compare.csv"],
    ["Day 15", "11/24", "3 张核心图定稿 + 宽幅空域图", "核心图统一 300 dpi；新增 13_airspace_wide.png（完整净空走廊 40×20 km）", "figures/00/03/05/13；scripts/make_airspace_wide.py"],
        ],
        widths=[1.4, 1.4, 3.2, 7.4, 3.6],
    )
    p(doc, "说明：11/18 为专家意见评审日，不计入 21 个执行日；Day 5–9 合并/提前到 11/20–11/22 完成。",
      size=9)

    # 2 结果
    h(doc, "2. 主要结果")

    h(doc, "2.1 网格与空域约束", 2)
    p(doc, "AOI 切分为 128 列 × 98 行 = 12,544 个 200 m 格（EPSG:32649）。"
           "机场净空保护区按深公规〔2017〕3 号（跑道中心线两侧各 10 km、端外 20 km）建走廊，"
           "覆盖 4,706 格（37.5%）；通告第一条是「严禁」施放无人机，因此按硬禁飞处理。"
           "连同梧桐山 144 格、深圳水库 132 格，硬禁飞共 4,982 格（39.7%）。")
    bullet(doc, "起终点吸附：核心 OD 罗湖—福田起点 91.7 m、终点 70.0 m；"
                "机场周边 4 组 OD 的端点吸附 1,254–6,380 m，判「端点落在硬禁飞区、不可达」，不挪端点凑可达。")
    bullet(doc, "判定阈值：吸附偏移 >300 m 一律判不可达；100–300 m 可运行但必须在报告中标注。")
    bullet(doc, "切角规则：对角移动要求两个正交邻格都畅通，避免「贴着禁飞区角切过去」。")

    h(doc, "2.2 最短路 baseline（λ=0，核心 OD + 扩展 OD 状态）", 2)
    table(
        doc,
        ["OD", "长度 km", "绕行率", "净空区内格数", "硬禁飞穿越", "状态"],
        [
            ["罗湖—福田（核心）", "7.014", "1.051", "0 / 34（0%）", "0", "可达"],
            ["北站—深圳湾", "—", "—", "—", "—", "不可达（终点吸附 1,856 m）"],
            ["福田 CBD—机场东", "—", "—", "—", "—", "不可达（终点吸附 5,945 m）"],
            ["南山—宝安", "—", "—", "—", "—", "不可达（2,802 / 5,395 m）"],
            ["宝安中心—南山", "—", "—", "—", "—", "不可达（6,380 / 1,254 m）"],
        ],
        widths=[4.8, 2.0, 2.0, 3.2, 2.4, 4.6],
    )

    h(doc, "2.3 λ=1 暴露加权 vs baseline", 2)
    p(doc, "核心 OD 长度 +7.09%（7.014 → 7.511 km），C 下降 33.05%。拆开看是两段："
           "λ≈0.025 起先在等长解里挑低暴露（长度不变、C −17.4%），λ≈0.825 起才是真绕行（多 497 m）。"
           "报告必须分开写，不能合并成一句「牺牲距离换安全」，也不能说 λ=1 是某个最优值。")
    table(
        doc,
        ["OD", "长度变化", "C λ=0（代理·米）", "C λ=1（代理·米）", "C 变化"],
        [
            ["罗湖—福田（核心）", "+7.09%", "3,922.2", "2,625.9", "−33.05%"],
        ],
        widths=[5.6, 2.8, 3.6, 3.6, 2.2],
    )
    p(doc, "C 是「等效暴露长度」，定义 C = Σ(边长 × 边暴露强度)，单位「代理·米」（proxy·m），"
           "可读作「假设全程以暴露强度 1.0 飞行，相当于飞了多少米」，恒有 C ≤ L；"
           "它与路线长度不可互换，也不是伤亡人数。平均暴露强度 E = C / L（无量纲），"
           "本次 E 由 0.5592 降到 0.3496。完整定义见仓库 docs/indicator_definition.md。", size=9)

    h(doc, "2.4 λ 扫描与 Pareto（核心 OD）", 2)
    table(
        doc,
        ["λ 区间", "长度 km", "C（代理·米）", "E = C/L", "解释"],
        [
            ["0（baseline）", "7.014", "3,922.2", "0.5592", "纯最短路"],
            ["0.025–0.80", "7.014", "3,241.5", "0.4621", "长度不变，等长解里挑低暴露（tie-break）"],
            ["0.825–2.0", "7.511", "2,625.9", "0.3496", "真绕行：+7.09% 距离，C −19.0%"],
        ],
        widths=[3.2, 2.2, 3.0, 2.2, 8.2],
    )
    p(doc, "去重规则：同一 OD 下格心序列逐格相同的算同一个解，等长但序列不同的算两个解"
           "（results/pareto_routes.csv 给了每条解的 hash）。核心 OD 81 档 λ 只有这 3 个解，"
           "2 个切换点是 0.025 / 0.825；"
           "明细与读法见仓库 docs/pareto_reading.md、figures/09_pareto_routes.png。", size=9)

    h(doc, "2.5 网格分辨率敏感性（核心 OD）", 2)
    table(
        doc,
        ["网格", "节点数", "长度 km", "绕行率", "沿路密度 λ=0→λ=1（人/km²）", "吸附偏移 起/终 m"],
        [
            ["100 m", "29,953", "7.114", "1.050", "30,190 → 17,878（−40.8%）", "36.6 / 17.9"],
            ["200 m（主）", "7,562", "7.014", "1.051", "30,050 → 18,388（−38.8%）", "91.7 / 70.0"],
            ["400 m", "1,894", "6.731", "1.044", "31,297 → 27,349（−12.6%）", "229.2 / 141.1"],
        ],
        widths=[2.6, 2.2, 2.2, 2.0, 6.2, 3.4],
    )
    p(doc, "跨分辨率不能直接比 C（随格面积与离散化一起变），所以同时报「沿路平均人口密度」与 E。"
           "400 m 两端吸附偏移 229/141 m，远超 100 m，报告中已标注。", size=9)
    p(doc, "补充实验（审核后，scripts/make_origin_shift.py）：把核心 OD 两端整体平移 ±0.5 格共 9 个位置，"
           "看结果对吸附位置的敏感性——C 最大变动 100 m ±1.6%、200 m ±3.6%、400 m ±20.8%；"
           "所以 400 m 只能当稳健性对照、不能当主结论，主实验维持 200 m。"
           "详见图 figures/08_origin_shift.png 与 results/origin_shift_summary.csv。", size=9)

    h(doc, "2.6 遮蔽系数敏感性与 SORA 对照（核心 OD，60 m）", 2)
    p(doc, "遮蔽系数 s 没有可引文献，因此不假设它是「真值」，而是看它把结论改变多少："
           "固定 s，扫描 λ=0–2（步长 0.025），找路线第一次切换的阈值。")
    table(
        doc,
        ["遮蔽系数 s", "实测切换阈值 λ", "1/(1−s) 预测", "不同路线数"],
        [
            ["0.2", "0.725", "0.722", "3"],
            ["0.3（主）", "0.825", "0.825", "3"],
            ["0.4", "0.950", "0.962", "3"],
        ],
        widths=[3.6, 4.4, 4.2, 3.0],
    )
    bullet(doc, "三组路线集合方向一致，只是阈值平移：遮蔽系数改变「何时开始绕」，"
                "不改变「绕比不绕更省暴露」的方向。")
    bullet(doc, "SORA 2.5 原文核对：目标地面风险 1E-6 致死/小时；iGRC 由最大人口密度分档"
                "（<25 到 >250000 人/km²）与无人机尺寸/速度决定；评估范围为运行体积 + 地面风险缓冲。"
                "「遮蔽」在 SORA 中是缓解措施 M1(A)，不是固定乘数。")
    bullet(doc, "因此本项目只把 0.30 当作工程假设，并在报告里写明：换成 0.2 或 0.4，"
                "结论方向不变、阈值移动；不宣称 0.30 是标准值。")

    h(doc, "2.7 Day 10：5 组走廊外 OD 批量（λ=0 vs λ=1）", 2)
    table(
        doc,
        ["OD", "长度 km", "长度变化", "C λ=0", "C λ=1", "C 变化", "结论"],
        [
            ["罗湖—福田（核心）", "7.014 → 7.511", "+7.09%", "3,922.2", "2,625.9", "−33.05%", "先 tie-break 后真绕行"],
            ["福田—罗湖", "7.014 → 7.511", "+7.09%", "3,649.5", "2,625.9", "−28.05%", "先 tie-break 后真绕行"],
            ["北站—福田", "7.883", "0.00%", "1,383.9", "1,361.3", "−1.63%", "仅等长 tie-break"],
            ["龙华—福田", "11.683 → 12.677", "+8.51%", "2,983.7", "1,928.2", "−35.38%", "真权衡：绕路换暴露"],
            ["布吉—罗湖", "5.697", "0.00%", "1,841.3", "1,468.5", "−20.25%", "仅等长 tie-break"],
        ],
        widths=[3.8, 3.0, 2.2, 2.4, 2.4, 2.2, 4.2],
    )
    p(doc, "批量图与明细：figures/10_batch_od.png、results/od_summary.csv。机场向 4 组 OD 在 2.1 中已判不可达，"
           "不参与批量；这本身说明「起降点不宜设在净空安全区内」。", size=9)

    h(doc, "2.8 Day 11：高度层与安全区尺寸情景", 2)
    table(
        doc,
        ["情景", "设置", "核心 OD 结果", "解释"],
        [
            ["高度 60 m", "alt_factor 1.00", "7.014 km；阈值 λ=0.825", "基准"],
            ["高度 90 m", "0.85", "7.014 km；阈值 0.950", "阈值 ≈ 0.825/0.85"],
            ["高度 120 m", "0.70", "7.014 km；阈值 1.175", "阈值 ≈ 0.825/0.70"],
            ["安全区 ×0.5", "半宽/端外延伸 ×0.5", "不可通行 1,160 格（9.3%）；机场向可达 1/4", "核心 OD 不受影响"],
            ["安全区 ×1.0", "官方尺寸", "4,982 格（39.7%）；0/4", "当前主口径"],
            ["安全区 ×1.5", "×1.5", "7,615 格（60.7%）；0/4", "只影响机场向"],
        ],
        widths=[2.6, 4.2, 6.0, 4.6],
    )
    bullet(doc, "高度情景只是把暴露整体乘一个常数，等价于把 λ 换成 λ·f：路线集合、跳变顺序都不变，"
                "所以只能报告「阈值平移」，不能报告「高度更安全」。")
    bullet(doc, "安全区是机场净空安全区的尺寸情景；当前把整条安全区当作单一主区（hard），"
                "主区/副区细分尚未建模（2026-11-23 决定先不建）。")
    bullet(doc, "两张图：figures/11_altitude_scenario.png、12_safety_area_scenario.png；"
                "明细：results/scenario_altitude*.csv、scenario_safety_area.csv。")

    # 3 决策
    h(doc, "3. 本周关键决策与依据（摘要）")
    table(
        doc,
        ["#", "决策", "依据 / 理由"],
        [
            ["1", "术语用「人口暴露代理」，不叫风险/安全", "模型不含失效概率与伤亡换算，专家意见第 1 条"],
            ["2", "核心实验 1 OD × 60 m 单层；3 层、5 OD 降为情景与扩展", "换层代价无依据；先把单层做可信"],
            ["3", "禁飞区删节点/删边 + 切角规则，不再用 1e6 惩罚", "惩罚不能保证 0 穿越；独立几何库复核"],
            ["4", "净空保护区按通告「严禁」改硬禁飞（2026-11-22）", "原文不是「需审批」；改后核心 OD 换罗湖—福田"],
            ["5", "C = Σ(边长×边暴露强度)，单位「代理·米」，另报 E = C/L；不报绝对伤害", "每公里失效概率近似相同时，期望伤害 ∝ C；但仍只做相对比较"],
            ["6", "边权 = 长度 ×(1+λ×暴露)，λ 无量纲", "便于解释与扫描；长度、暴露分两列报告"],
            ["7", "主网格 200 m；100/400 m 只做敏感性", "公开人口数据 100 m 与计算量折中"],
            ["8", "λ≈0.825（s=0.30）为真绕行阈值，但不宣称最优 λ", "81 档 λ 只有 3 个解，阈值是观察结果"],
            ["9", "OD 坐标为手工近似，逐个报告吸附偏移", "无门牌级权威坐标；不编造精度"],
            ["10", "机场周边 4 组 OD 判不可达，不挪端点", "端点落在硬禁飞区；挪点等于改题"],
            ["11", "主数据用 WorldPop 2020，合成仅作离线 fallback", "Day 14 下载并校验 625 MB 栅格；真实数据让 λ=1 变成真绕行"],
            ["12", "文献引用必须可核对（DOI/文号/原文页），不引二手转述", "11 条全部核对过"],
            ["13", "遮蔽系数 0.30 只作工程假设，另做 0.2/0.3/0.4 敏感性", "SORA 中遮蔽是缓解措施 M1，不是固定系数"],
            ["14", "仓库公开、README v0.3、一键 13 步脚本", "新克隆 10 分钟内跑通是验收标准之一"],
            ["15", "测试补到 62 项（risk/grid/mask/router/metrics/graph/config/情景/CLI/日志）", "审核要求覆盖 4 类核心逻辑，实际多补 5 类"],
        ],
        widths=[1.0, 7.4, 8.6],
    )
    p(doc, "完整 25 条决策与日期见仓库 docs/decisions.md；假设与不适用范围见 docs/assumptions.md。", size=9)

    # 4 证据
    h(doc, "4. 证据与可复现")
    table(
        doc,
        ["项目", "结果"],
        [
            ["提交记录", "从 2b266ed（Day 1）到当前 HEAD；main 与 origin/main 一致"],
            ["测试", "pytest 62 项通过：mask 11、graph 5、router 6、metrics 6、risk 9、grid 8、config 4、情景 3、CLI 6、日志 4"],
            ["一键复现", "scripts/run_all.py 13 步全过，实测 117.2 s"],
            ["公开仓库", "https://github.com/yir97166/lowalt-route-risk（Public，SSH over 443）"],
            ["全新克隆", "安装约 2 分钟 + 脚本全过，退出码 0，pip check 干净"],
            ["可复现", "合成数据路径已逐字节验证；真实数据重跑由脚本重生成，无随机步骤"],
            ["独立复核", "每条路线用 shapely 独立校验：相邻步长、硬禁飞格、逐段相交、最小间距"],
            ["人工抽查", "用户 2026-11-20 核对 λ=1 旧核心 OD；11-22/11-23 抽查通过"],
        ],
        widths=[3.4, 13.4],
    )

    # 5 局限
    h(doc, "5. 局限、风险与未验证项")
    table(
        doc,
        ["局限", "影响", "处理"],
        [
            ["人口为 WorldPop 2020 建模估计", "绝对数字不是普查值，仍有不确定性", "只做相对比较；报告显著标注"],
            ["净空区按「严禁」作硬禁飞", "仍是模型简化，不等于具体飞行获批", "报告写明「非合规判断」"],
            ["安全区未分主区/副区", "无法表达「主区严禁、副区限制」的分层", "按单一主区处理并写明；副区待有划分依据再做"],
            ["4 组扩展 OD 不可达", "无法给机场接驳路线", "如实记为端点落在净空区；不挪端点"],
            ["核心实验仅 60 m 单层", "无法回答高度权衡", "3 层只作 Day 11 情景，标注假设"],
            ["λ=1 同时跨两段机制", "易被误读成单一数字或最优 λ", "拆成 0.025 起 tie-break、0.825 起真绕行两段"],
            ["400 m 两端偏移 229/141 m，C 变动 20.8%", "粗网格代表性下降", "报告标注，主实验用 200 m"],
            ["通信/电磁干扰未建模", "真实运行的重要风险缺失", "写入局限；有频谱数据可作第二层"],
            ["失效概率、坠落轨迹未知", "不能换算伤亡", "只做相对比较，不报绝对风险"],
            ["未按 SORA 做定量评估", "不能声称符合 SORA", "只把 SORA 当参照，报告写明「非审定/非合规」"],
            ["遮蔽 0.30 无实测依据", "换系数会移动阈值", "已做 0.2/0.3/0.4 敏感性；结论方向不变"],
        ],
        widths=[4.6, 6.2, 6.0],
    )

    # 6 下周
    h(doc, "6. 下阶段计划（Day 16–19）")
    table(
        doc,
        ["天", "任务", "产出 / 验收"],
        [
            ["Day 16", "中文技术报告初稿（6–8 页）", "report/report_zh.md 完成稿"],
            ["Day 17", "英文摘要 + 图表定稿", "report/abstract_en.md"],
            ["Day 18", "新克隆测试、依赖/路径修复", "10 分钟内跑通"],
            ["Day 19", "3 分钟英文视频", "report/demo.mp4"],
        ],
        widths=[1.6, 9.0, 6.2],
    )

    # 7 问题
    h(doc, "7. 请专业人士重点看的 6 个问题")
    for q in [
        "Q1 用「人口暴露代理 + 累计暴露」做路线比较，在学术上是否有更标准的指标或必须补的项？",
        "Q2 核心 OD 上 λ=1 同时含等长 tie-break 与真绕行（+7.09% / C −33.05%），阈值 0.825——这个分解站得住吗？还是网格对称性造成的假象？",
        "Q3 净空保护区按通告原文「严禁」作硬禁飞、核心 OD 换到罗湖—福田、机场 4 组 OD 判不可达——这个处理是否可辩护？",
        "Q4 遮蔽 0.30 只是工程假设（SORA 里遮蔽属于缓解措施 M1，不是固定乘数）。"
        "在不能拿到实测数据时，是把 0.30 写死并做敏感性，还是干脆去掉遮蔽？",
        "Q5 我们不按 SORA 做定量评估（iGRC 分档 vs 连续暴露未映射），只当参照。"
        "这个边界在硕士申请作品里是否够诚实、够用？",
        "Q6 通信/电磁干扰没有数据就不建模、只写局限，这样的处理在审稿/答辩中是否足够？",
    ]:
        para = p(doc, q)
        para.paragraph_format.space_before = Pt(0)
        ans = p(doc, "专家意见：", size=9)
        ans.paragraph_format.space_after = Pt(0)

    # 8 附件
    h(doc, "8. 附件与路径")
    p(doc, "公开仓库：https://github.com/yir97166/lowalt-route-risk")
    p(doc, "包内材料：01_原始资料（通告 + 4 张航图）、02_专家审核（意见、审核包 v1.2、本周报）、"
           "03_图与结果_20261122（全部图与核心 CSV）。仓库内另见 docs/literature.md、docs/decisions.md。", size=9)
    p(doc, "复现：`.\\venv\\Scripts\\python.exe scripts\\run_all.py`（13 步，约 117.2 s）；"
           "`-m pytest -q`（62 passed）。验收口径：一键从零全过、测试全绿、CSV/PNG 由脚本重生成；"
           "所有数字以仓库 results/ 与 figures/ 为准，本报告不手改数字。", size=9.5)
    p(doc, "免责声明：本项目为方法演示与能力证明；人口数据为 WorldPop 2020 建模估计、禁飞区为示意或公开资料近似，"
           "不构成适航审定、运行许可、合规判断或任何实际飞行依据。", size=9)
    doc.save(OUT)
    print(f"written: {OUT}")
    return doc


if __name__ == "__main__":
    build()
