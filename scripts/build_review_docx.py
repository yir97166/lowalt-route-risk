# -*- coding: utf-8 -*-
"""生成「项目计划 + Day 1 产出」审核稿（docx）。一次性工具脚本。"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT_DIR = Path(r"C:\Users\弋昊阳\OneDrive\桌面\low-attitude report\02_专家审核\20261119_审核包_v1.2")
DOCX = OUT_DIR / "低空航路规划原型-计划与Day1产出-审核稿.docx"
FIG = Path(
    r"C:\Users\弋昊阳\OneDrive\文档\deepseek-harness\default-workspace"
    r"\lowalt-route-risk\figures\00_population.png"
)

CN_FONT = "微软雅黑"


def set_style_font(style, size, bold=False, color=None):
    style.font.name = CN_FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    if color:
        style.font.color.rgb = RGBColor.from_string(color)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), CN_FONT)


def shade(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color)
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


def cell_text(cell, text, bold=False, size=9):
    cell.text = ""
    para = cell.paragraphs[0]
    para.paragraph_format.space_after = Pt(0)
    run = para.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = CN_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)


def add_table(headers, rows, widths_cm, font_size=9, header_fill="DCE6F1"):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_row = table.rows[0]
    tr_pr = header_row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))  # 跨页时重复表头
    for idx, header in enumerate(headers):
        cell = header_row.cells[idx]
        cell_text(cell, header, bold=True, size=font_size)
        shade(cell, header_fill)
    for row in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            cell_text(cells[idx], str(value), size=font_size)
    for row in table.rows:  # 行不跨页断开
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    fix_widths(table, widths_cm)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def h(text, level=1):
    heading = doc.add_heading(text, level=level)
    return heading


def p(text, bold=False, size=None, color=None, align=None, space_after=4, keep_with_next=False):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(space_after)
    para.paragraph_format.keep_with_next = keep_with_next
    if align is not None:
        para.alignment = align
    run = para.add_run(text)
    run.font.bold = bold
    run.font.name = CN_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
    if size:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    return para


def bullet(text, size=10):
    para = doc.add_paragraph(style="List Bullet")
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run(text)
    run.font.name = CN_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
    run.font.size = Pt(size)
    return para


def add_footer_page_number():
    footer = doc.sections[0].footer
    para = footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run("低空航路规划原型 · 审核稿 v1.1 · 第 ")
    run.font.size = Pt(8)
    run.font.name = CN_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
    run2 = para.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run2._r.append(fld_begin)
    run2._r.append(instr)
    run2._r.append(fld_end)
    run3 = para.add_run(" 页")
    run3.font.size = Pt(8)
    run3.font.name = CN_FONT
    run3._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)


def mono(text):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    return para


doc = Document()
section = doc.sections[0]
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.left_margin = Cm(2.0)
section.right_margin = Cm(2.0)
section.top_margin = Cm(1.8)
section.bottom_margin = Cm(1.8)

set_style_font(doc.styles["Normal"], 10.5)
set_style_font(doc.styles["Heading 1"], 15, bold=True, color="1F3864")
set_style_font(doc.styles["Heading 2"], 12, bold=True, color="2E5496")
set_style_font(doc.styles["List Bullet"], 10)

add_footer_page_number()

# ---------------------------------------------------------------- 标题
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_before = Pt(6)
run = title.add_run("低空航路规划原型")
run.font.size = Pt(24)
run.font.bold = True
run.font.name = CN_FONT
run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run("项目计划与 Day 1 产出 · 审核稿 v1.1")
run.font.size = Pt(14)
run.font.name = CN_FONT
run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = meta.add_run("弋昊阳 ｜ 2026-11-19 ｜ 深圳中西部 25×19 km ｜ 200 m 网格 ｜ 3 层高度 ｜ 21 天")
run.font.size = Pt(9)
run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
run.font.name = CN_FONT
run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

doc.add_paragraph()

# ---------------------------------------------------------------- 如何审阅
h("如何审阅（约 30 分钟）", 1)
bullet("第 0、1 节（5 分钟）：看范围和定位是否合理，是否承诺过多。")
bullet("第 2、5 节（15 分钟）：看方法是否站得住、六个参数是否有依据，这是最需要专家意见的地方。")
bullet("第 3 节（5 分钟）：看 21 天时间安排是否现实。")
bullet("第 7 节（5 分钟）：10 个问题下面留了空白，可直接写意见或口头反馈。")

# ---------------------------------------------------------------- 0 摘要
h("0. 一页摘要", 1)
p(
    "本项目从 2026-11-17 开始，21 天内（至 12-08；Day 1 已提前完成，实际执行 20 个工作日）"
    "做一个可复现的低空航路规划原型：在深圳中西部约 "
    "25×19 km 范围内，用 200 m 网格和 60 / 90 / 120 m 三层高度，把人口数据转成地面风险面，"
    "叠加 3 个（示意）禁飞区，比较「最短路径」与「风险规避路径」，并用 λ 扫描得到风险—距离 "
    "Pareto 前沿。最终产出 GitHub 仓库、6–8 页中文报告、3 张核心图和 3 分钟英文视频，"
    "用于硕士（低空经济 / UTM 方向）申请作品集。"
)
p(
    "研究问题（RQ）：在给定人口地面风险与 3 个禁飞区约束下，绕行多少距离能换来多少风险下降？"
    "60 / 90 / 120 m 三层高度里，哪一层的「风险—距离」性价比最好？",
    size=10,
)
bullet("定位：方法演示与能力证明，不是适航审定，不是运行系统，不做实时空域、气象、多机协同。")
bullet("边界：所有禁飞区均为 illustrative only（手工多边形），不代表官方划设。")
bullet("进度：Day 1 已完成——环境、数据（降级合成）、128×98 网格、人口热力图。")
bullet("可复现：全新克隆实测 3 分钟内跑通，输出 CSV/PNG 与本地逐字节一致（第 8 节）。")

# ---------------------------------------------------------------- 1 边界
h("1. 项目边界：做什么，不做什么", 1)
add_table(
    ["做", "不做"],
    [
        ["2D 网格 + 3 层高度的路径规划", "实时空域、动态禁飞、临时管制"],
        ["人口地面风险面（相对值 0–1）", "气象风场、降雨、能见度"],
        ["3 个示意禁飞区的硬约束", "完整 SORA 定量审定与文件包"],
        ["5 组起降点、λ 扫描、Pareto 前沿", "多机协同、冲突解脱"],
        ["高度 / λ / 缓冲的敏感性分析", "前端 UI、在线服务"],
        ["单元测试 + 一键复现", "真实空管数据接入、适航取证"],
        ["中文报告 + 英文摘要 + 3 分钟视频", "真实飞行验证"],
    ],
    [8.5, 8.5],
)

p("三个刻意简化（会写进报告「边界」一节）：", bold=True, size=10)
bullet("只算地面人员风险，不含无人机空中相撞（air-to-air）与噪音、隐私等维度。", size=9)
bullet("不建模转弯半径、爬升率等动力学；层间换层只按等效距离计。", size=9)
bullet("高度按 AGL 简化，不扣地形起伏（深圳西部地势平坦，量级影响可接受）。", size=9)

h("1.1 最终交付物（12/08 前）", 2)
add_table(
    ["交付物", "形式", "验收标准"],
    [
        ["GitHub 仓库", "公开 repo + README", "全新克隆按 README 10 分钟内跑通"],
        ["中文报告", "report/report_zh.pdf，6–8 页", "含方法、结果、假设、局限、失败模式"],
        ["英文摘要", "1 页", "术语准确、无明显语病"],
        ["3 张核心图", "PNG ≥300 dpi", "人口热力图、路线对比、Pareto"],
        ["3 分钟英文视频", "report/demo.mp4", "画面清楚、讲解完整"],
        ["单元测试", "pytest", "风险 / 图 / 掩膜 / 路线 4 类逻辑全绿"],
    ],
    [3.4, 6.2, 7.4],
    font_size=8.5,
)

# ---------------------------------------------------------------- 2 技术方案
h("2. 技术方案", 1)

h("2.1 空间范围与网格", 2)
add_table(
    ["项目", "取值", "说明"],
    [
        ["研究区 bbox", "113.85–114.10°E，22.48–22.65°N", "约 25×19 km，深圳中西部"],
        ["投影", "EPSG:32649（UTM 49N）", "米制距离，误差 <0.1%"],
        ["网格", "200 m × 200 m，128 列 × 98 行", "共 12,544 格，行 0 在北"],
        ["高度层", "60 / 90 / 120 m AGL", "3 层，掩膜前共 37,632 个节点"],
        ["邻接", "平面 8 邻域；层间垂直边", "垂直边等效代价 50 m，不乘风险系数"],
        ["起降点", "5 组 OD，见 configs/aoi.yaml", "深圳北—深圳湾、福田 CBD—宝安机场东、南山—宝安、罗湖—福田、宝安中心—南山"],
    ],
    [3.6, 6.8, 6.6],
)

h("2.2 数据", 2)
bullet(
    "WorldPop 2020 中国 100 m 约束版（计划用真实数据）。Day 1 实测：文件 625 MB，"
    "90 秒内连 4 MB 数据块都取不到，按计划降级为合成数据。"
)
bullet(
    "合成数据：5 个高斯人口团（福田、南山、宝安中心、深圳北、罗湖），背景 50 人/100 m 像元，"
    "峰值约 1,366 人/像元，AOI 总人口约 512 万，与深圳实际量级同阶。"
)
bullet("禁飞区：宝安机场周边 5 km 圆（示意缓冲，非净空保护区几何）+ 梧桐山、深圳水库两个矩形（示意，非官方）。")
bullet(
    "数据引用：WorldPop (2020), Global 2000–2020 Constrained Individual Countries, 100 m"
    "（www.worldpop.org）；只使用聚合栅格，不含个人信息。"
)
bullet(
    "合成数据可复现：scripts/make_synthetic_data.py 固定随机种子 42；"
    "网格人口总和 5,124,821 与源栅格总和 5,136,125 相差 0.22%（边缘无数据格），说明面积加权正确。"
)
bullet(
    "真实数据接入：把 GeoTIFF 放到 data/raw/worldpop/chn_ppp_2020_100m.tif 后重跑，"
    "src/data.py 会自动优先使用真实栅格，无需改代码。"
)

h("2.3 地面风险模型", 2)
p("pop_norm = min(pop_cell / p95, 1)，p95 取非零格的 95 分位数（抗离群）。", size=10)
p("risk_cell = pop_norm × severity × (1 − shelter) × alt_factor", size=10)
bullet("severity = 1.0（只做相对比较，不折算绝对伤亡）。")
bullet("shelter = 0.30（地面遮蔽，工程近似，需专家确认）。")
bullet("alt_factor：60 m = 1.00，90 m = 0.85，120 m = 0.70（越高地面暴露越低）。")
bullet("适用范围：risk 只表示地面人员暴露的相对强度，不含空中相撞、噪音、隐私等维度。")
p("含义：risk ∈ [0,1]，表示该格在 60 m 层的相对地面暴露强度；用于路径代价，不用于绝对定量。", size=10)

h("2.4 图与路径代价", 2)
bullet("平面 8 邻域：直边 200 m，斜边 200√2 m。")
bullet("边代价 = 长度 × (1 + λ × risk)；λ = 0 为最短路，λ 越大越避让人群。")
bullet("垂直边：层间换层等效 50 m 代价，不乘风险（待确认，见 Q5）。")
bullet("禁飞区：格点不可通行，硬惩罚 1e6，保证 0 次穿越。")
bullet("对比实验：λ = 0（最短）vs λ = 1（风险规避）；另做 λ 从 0 到 2 的加密扫描（Day 6 实现，步长 0.1；config 里现在先放 0/0.5/1/1.5/2 五个点）。")

h("2.5 实验矩阵与指标", 2)
bullet("实验规模：5 组 OD × 3 个高度层 = 15 条主航线；另做 λ、高度、禁飞缓冲倍数的敏感性（缓冲倍数 Day 11 定）。")
bullet("指标：总距离、累计风险暴露（Σ risk × 边长，单位 m 的相对量）、穿越禁飞区次数、绕行率、Pareto 前沿。")
bullet("绕行率定义：(路线长度 − 起终点直线距离) / 直线距离；Pareto 用「累计风险暴露 vs 总距离」。")
bullet("目标值：风险降低 ≥30%，距离增加 ≤20%（跑完按实际数据修正，不达标就如实报告）。")

h("2.6 复现方式", 2)
mono("python -m venv .venv")
mono(r".\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
mono(r".\.venv\Scripts\python.exe scripts\make_synthetic_data.py")
mono(r".\.venv\Scripts\python.exe scripts\make_population_map.py")
p("环境：Python 3.12.10；numpy 2.2.6 / pandas 3.1.1 / rasterio 1.5.2 / networkx 3.7 / matplotlib 3.11.2；pip check 通过。", size=9)
p("依赖说明：requirements.txt 用 >= 下限约束（便于他人安装）；上列为本机实测版本，若新版本出现 API 差异，以实测版本为准。镜像参数仅为加速，海外网络可去掉 -i。", size=9)

h("2.7 结果如何自证（核验清单）", 2)
bullet("硬约束断言：每条路线 0 次穿越禁飞区（pytest 断言，Day 9 落地）。", size=9)
bullet("下界对照：路线长度 ≥ 起终点直线距离；绕行率异常（>2）的航线人工复核。", size=9)
bullet("确定性复跑：固定种子下重跑两次，路线与指标完全一致。", size=9)
bullet("逐字节复现：全新克隆跑出的 grid_population.csv 与本地 SHA256 一致（见第 8 节）。", size=9)
bullet("人工抽查：Day 6 由你手算 1 条路线的距离/风险，与程序输出对照。", size=9)

# ---------------------------------------------------------------- 3 计划
h("3. 21 天执行计划", 1)
p(
    "Day 1 已于 11/17 提前完成；Day 2 从 11/19 开始，至 12/08 结束，共 20 个工作日，"
    "12/08 保留为缓冲日。原则：先跑通 2D，再加高度层；第 14 天必须发布 v1，不憋完美。"
    "每日投入 2–3 小时。",
    size=10,
)

plan_rows = [
    ["1", "11/17", "环境、repo、数据、第一张图", "00_population.png", "图能出、数字合理"],
    ["2", "11/19", "200 m 网格、禁飞掩膜、高度层", "网格 + 禁飞区图", "掩膜内 0 个可通行格"],
    ["3", "11/20", "建图 + 最短路 baseline", "第一条路线图", "5 组 OD 全可达"],
    ["4", "11/21", "风险加权代价 + 对比", "baseline vs 风险路线 + 指标表", "0 次穿越禁飞区"],
    ["5", "11/22", "3 层高度 + 3D 图", "3D 路线图", "换层位置可解释"],
    ["6", "11/23", "λ 扫描 + Pareto", "Pareto 图 + 敏感性表", "曲线单调可解释"],
    ["7", "11/24", "周复盘、README v0.1、发布", "可展示 v0.1", "新克隆 10 分钟跑通"],
    ["8", "11/25", "风险模型细化（遮蔽/后果/高度）", "risk.py v0.2", "参数有书面依据"],
    ["9", "11/26", "单元测试：风险/图/掩膜/路线", "pytest 全绿", "覆盖 4 类核心逻辑"],
    ["10", "11/27", "5 组 OD 批量实验", "results/od_summary.csv", "结果表无缺失"],
    ["11", "11/28", "高度 / λ / 缓冲敏感性", "敏感性表 + 图", "每参数可解释"],
    ["12", "11/29", "代码整理、CLI、config", "一键跑通", "一条命令复现全部结果"],
    ["13", "11/30", "异常处理、日志、随机种子", "可复现", "同种子结果一致"],
    ["14", "12/01", "中期复盘、定稿 3 张图", "报告方法/结果初稿", "图可直接进报告"],
    ["15", "12/02", "报告全文（中文）", "6–8 页初稿", "含假设/局限/失败模式"],
    ["16", "12/03", "英文摘要 + 图表定稿", "report/abstract_en.md", "英文通顺无硬伤"],
    ["17", "12/04", "新克隆测试、依赖/路径修复", "10 分钟内跑通", "干净环境通过"],
    ["18", "12/05", "录 3 分钟英文视频", "report/demo.mp4", "画面清楚、讲解完整"],
    ["19", "12/06", "找 2 人挑刺、列修改清单", "反馈清单", "至少 5 条可执行意见"],
    ["20", "12/07", "发布 GitHub、CV/PS 段落", "公开链接 + 文案", "链接可访问"],
    ["21", "12/08", "缓冲、复盘、决定 stretch goal", "复盘笔记", "明确是否加练"],
]
add_table(
    ["天", "日期", "任务", "当日产出", "验收标准"],
    plan_rows,
    [0.9, 1.8, 5.8, 5.0, 3.5],
    font_size=8.5,
)

h("3.1 第一周逐日怎么做（Day 2–7）", 2)

p("Day 2（11/19）网格与禁飞掩膜", bold=True, size=10)
bullet("做法：bbox 对齐 200 m 网格（UTM 49N）；3 个禁飞区栅格化为不可通行掩膜；出网格+掩膜图。", size=9)
bullet("产出：figures/01_grid_nofly.png；掩膜函数进 src/grid.py；配套测试。", size=9)
bullet("验收：12,544 格；图与 configs 一致；掩膜内 0 个可通行格。", size=9)
bullet("你要做：查机场周边限飞/净空要求，确认 5 km 圆形缓冲是否合理（decisions.md 第 5 条）。", size=9)

p("Day 3（11/20）建图 + 最短路", bold=True, size=10)
bullet("做法：8 邻域建图（12,544 × 3 节点）；networkx 求 5 组 OD 最短路；出第一条路线图。", size=9)
bullet("产出：figures/02_shortest_path.png；results/baseline.csv。", size=9)
bullet("验收：5 组 OD 全部可达；0 次穿越禁飞区；距离与直线距离之比合理（<1.6）。", size=9)
bullet("你要做：定 5 组起降点坐标与来源，自己提交 aoi.yaml。", size=9)

p("Day 4（11/21）风险加权路径", bold=True, size=10)
bullet("做法：边权改为 length × (1 + λ × risk)；λ=1 与 λ=0 对比；输出指标表。", size=9)
bullet("产出：figures/03_route_compare.png；results/compare.csv（距离/风险/绕行率）。", size=9)
bullet("验收：结果可复现；风险下降与距离增加的关系能解释。", size=9)
bullet("你要做：写 λ=1 的三行理由（decisions.md 第 4 条）。", size=9)

p("Day 5（11/22）三层高度 + 3D", bold=True, size=10)
bullet("做法：平面图复制到 3 层；层间垂直边；3D 轨迹图。", size=9)
bullet("产出：figures/04_3d_route.png；src/graph.py 分层逻辑。", size=9)
bullet("验收：垂直边代价一致；3D 图能看出换层位置与原因。", size=9)
bullet("你要做：查 120 m 高度层有没有法规/文件说法。", size=9)

p("Day 6（11/23）λ 扫描 + Pareto", bold=True, size=10)
bullet("做法：λ 0–2 步长 0.1 扫描；画「距离 vs 风险」Pareto。", size=9)
bullet("产出：figures/05_pareto.png；results/pareto.csv。", size=9)
bullet("验收：曲线单调/可解释；拐点能指出对应 λ。", size=9)
bullet("你要做：手工核对一条路线的距离与风险（用坐标手算或表格核对）。", size=9)

p("Day 7（11/24）周复盘 + v0.1", bold=True, size=10)
bullet("做法：整理代码、README、结果；打 tag v0.1；push。", size=9)
bullet("产出：GitHub 可展示版本。", size=9)
bullet("验收：新克隆按 README 10 分钟内跑通。", size=9)
bullet("你要做：写半页周复盘 + README 项目简介段。", size=9)

# ---------------------------------------------------------------- 4 Day1
doc.add_page_break()
h("4. Day 1 已完成产出（2026-11-17）", 1)

add_table(
    ["指标", "结果", "说明"],
    [
        ["网格", "128 列 × 98 行，200 m", "12,544 格，EPSG:32649"],
        ["人口栅格（合成）", "170 × 250 像元", "均值 120.8 人/像元，峰值 1,366"],
        ["AOI 总人口", "约 512 万", "量级与深圳实际可比"],
        ["p95（非零格）", "1,794.28 人/格", "归一化基准"],
        ["最大格人口", "4,470.6 人", "约 11 万人/km²，高层密集区量级"],
        ["60 m 风险面最大值", "0.700", "p95 截断 + 遮蔽 + 高度因子"],
        ["非零人口格", "12,197 / 12,544", "边缘格无数据"],
    ],
    [4.6, 6.2, 6.2],
)

p("图 1：200 m 网格人口热力图（合成数据，log10 显示），标注起降点、机场周边 5 km 圆形缓冲（示意）与两个示意敏感区。", size=9, align=WD_ALIGN_PARAGRAPH.CENTER)
if FIG.exists():
    doc.add_picture(str(FIG), width=Cm(16.5))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
else:
    p("（图缺失）", size=9)

p("Day 1 交付文件：", bold=True, size=10)
add_table(
    ["文件", "作用"],
    [
        ["src/config.py", "读 configs/aoi.yaml，强类型配置 + 校验"],
        ["src/grid.py", "200 m 网格构建、格心与经纬度互转"],
        ["src/data.py", "人口栅格按面积加权重采样到网格（真实/合成自动切换）"],
        ["src/risk.py", "人口归一化 + 风险面公式"],
        ["src/viz.py", "热力图绘制（含禁飞区、起降点、底图裁剪）"],
        ["scripts/make_population_map.py", "一键：数据 → 图 + CSV"],
        ["scripts/make_synthetic_data.py", "合成人口栅格生成"],
        ["docs/assumptions.md", "8 类假设与不适用范围"],
        ["docs/decisions.md", "6 个关键参数的决策记录（待你填写）"],
        ["docs/contributions.md", "个人贡献台账（待你填写）"],
        ["figures/00_population.png", "Day 1 核心产出图"],
    ],
    [6.6, 10.4],
    font_size=8.5,
)

p("已知局限（必须写进报告「局限」一节）：", bold=True, size=10)
bullet("人口为合成数据，不是真实 WorldPop；只能证明流程，不能用于实际结论。", size=9)
bullet("禁飞区为手工示意多边形，不代表官方划设。", size=9)
bullet("机场 5 km 圈圆心在 AOI 西侧，图上只露出左边缘一小段。", size=9)
bullet("尚未做路由、敏感性、Pareto；30% 风险降幅目标尚未验证。", size=9)
bullet("未做性能优化，单线程运行。", size=9)

# ---------------------------------------------------------------- 5 假设
h("5. 六个关键假设（最需要专家意见）", 1)
add_table(
    ["参数", "当前值", "依据现状", "希望专家判断"],
    [
        ["地面遮蔽系数", "0.30", "工程近似，来自 SORA 地面风险的常见简化", "0.3 偏保守还是偏乐观？有没有更合适取值"],
        ["高度因子", "1.00 / 0.85 / 0.70", "越高地面暴露越低的工程假设", "比例是否有依据？120 m 以下随高度怎么变"],
        ["归一化方式", "人口 p95", "抗离群，保证 risk ∈ [0,1]", "p95 是否合适？是否该用分位数或对数"],
        ["风险权重 λ", "默认 1.0", "便于对比与扫描", "λ 的物理含义？量纲如何解释"],
        ["机场周边缓冲", "5 km 圆", "常识性取值，非官方净空几何", "实际限飞/净空要求多大？5 km 是否合理"],
        ["后果严重度", "1.0", "只做相对比较", "接受「不算绝对伤亡」这个简化吗"],
    ],
    [3.4, 3.6, 5.4, 4.6],
    font_size=8.5,
)

# ---------------------------------------------------------------- 6 风险
h("6. 主要风险与降级方案", 1)
add_table(
    ["风险", "概率", "降级方案"],
    [
        ["WorldPop 下载失败（已发生）", "高", "合成数据先跑通；有空再换真实数据"],
        ["GIS 依赖装不上", "中", "纯 numpy 网格 + matplotlib，方法不变"],
        ["范围失控 / 时间被考试挤掉", "高", "冻结 MVP，走 10 天版本"],
        ["风险降幅达不到 30%", "中", "调整 λ/高度/缓冲；如实报告负结果"],
        ["3D / Pareto 做不完", "中", "先保 2D + 1 层 + 1 组 OD，再迭代"],
    ],
    [7.4, 2.2, 7.4],
)

# ---------------------------------------------------------------- 7 问题
h("7. 请专家重点回复的 10 个问题", 1)
questions = [
    "Q1 风险公式用「人口 × 遮蔽 × 高度」连乘是否合理？SORA 或文献里地面风险通常怎么建模？遮蔽取常数 0.30 是否可接受？",
    "Q2 高度因子 60/90/120 m 取 1.00/0.85/0.70 有无依据？低空（<120 m）地面风险随高度如何变化更合理？",
    "Q3 归一化用非零格 p95 是否合适？会不会掩盖高密度区差异？建议改用哪种归一化？",
    "Q4 边代价「长度 × (1 + λ × risk)」的能量/时间解释是什么？λ 应该怎么定、怎么解释量纲？",
    "Q5 层间垂直边按等效 50 m 代价、不乘风险系数，是否会造成不合理绕飞或换层？",
    "Q6 禁飞区用示意多边形、标注 illustrative only，在作品集/论文场景是否可以接受？会不会被质疑不严谨？",
    "Q7 5 组 OD（深圳北—深圳湾、福田 CBD—宝安机场东、南山—宝安、罗湖—福田、宝安中心—南山）代表性够吗？是否应增加机场—市区这类典型航线？",
    "Q8 如果风险降幅只有 10–20%（不达 30%），应该怎样呈现？「负结果」怎么写才有价值？",
    "Q9 为什么用「网格 + Dijkstra」而不是 A*、RRT*、PRM？在 200 m 网格、3 层高度下，这个选择会不会被认为过于简单？",
    "Q10 200 m 网格和 25×19 km 范围合适吗？网格再粗/再细、范围再大，会怎样影响结论与可信度？",
]

for idx, question in enumerate(questions, start=1):
    p(question, size=10, keep_with_next=True)
    p("专家意见：", size=9, color="808080", space_after=2, keep_with_next=True)
    p("", size=9, space_after=6)

# ---------------------------------------------------------------- 8 自检
doc.add_page_break()
h("8. 自检记录（2026-11-19 交付前重跑）", 1)
p("这一节是我交付前重新跑过的核验，供专家抽查；没验证的事项也列在最后。", size=10)
add_table(
    ["核验项", "方法", "结果"],
    [
        ["统计数字", "独立脚本重算 data/processed/grid_population.csv",
         "总人口 5,124,820.8；p95 1,794.284；最大格 4,470.6；非零格 12,197；risk max 0.700——与正文一致"],
        ["源数据一致性", "合成栅格总和 vs 网格总和",
         "5,136,125 vs 5,124,821，差 0.22%（边缘无数据格），面积加权正确"],
        ["环境", "pip check + 版本核对",
         "No broken requirements；版本与 2.6 一致"],
        ["全新克隆复现", "git clone → 新建 venv → 镜像安装 → 跑两个脚本",
         "安装 150.9 s + 运行 15.3 s，exit 0；CSV 与 PNG 的 SHA256 与本地完全一致"],
        ["文档一致性", "抽取正文核对日期/OD/数字",
         "无 11/18 残留；日期、5 组 OD、页数与正文一致"],
    ],
    [3.0, 6.4, 7.6],
    font_size=8.5,
)
p("尚未验证 / 已知缺口：", bold=True, size=10)
bullet("真实 WorldPop 未接入，人口数字只对合成数据成立。", size=9)
bullet("路线、禁飞掩膜、Pareto 尚未实现（Day 2 起），30% 风险降幅未验证。", size=9)
bullet("文献依据未系统整理（Day 8 补 5–10 篇：SORA、低空地面风险评估）。", size=9)
bullet("三分钟英文视频与报告尚未开始（Day 15–18）。", size=9)
bullet("安装耗时依赖网络，换网络/镜像会变；命令本身已验证。", size=9)

# ---------------------------------------------------------------- 9 附录
h("9. 附录：运行方式与文件位置", 1)
p("项目根目录：", bold=True, size=10)
p(r"C:\Users\弋昊阳\OneDrive\文档\deepseek-harness\default-workspace\lowalt-route-risk", size=9)

p("复现命令（PowerShell）：", bold=True, size=10)
mono("python -m venv .venv")
mono(r".\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
mono(r".\.venv\Scripts\python.exe scripts\make_synthetic_data.py")
mono(r".\.venv\Scripts\python.exe scripts\make_population_map.py")

p(
    "声明：本项目为方法演示与能力证明，所有禁飞区、人口数据均为示意或合成，"
    "不构成适航审定、运行许可或任何实际飞行依据。",
    size=9,
    color="7F7F7F",
)

OUT_DIR.mkdir(parents=True, exist_ok=True)
doc.save(str(DOCX))
print(f"written: {DOCX}")
