"""把核心 OD 的 λ 扫描结果做成一个带说明的 Excel，方便非技术读者核对。

用途：用户抽查 λ=1 那一行，确认 14.665 km / 2.727。
"""
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "core_od_lambda_sweep.csv"
OUT = ROOT / "results" / "core_od_lambda_sweep.xlsx"

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(name="微软雅黑", bold=True, color="FFFFFF", size=10)
BODY_FONT = Font(name="微软雅黑", size=10)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center")


def main() -> None:
    with SRC.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]

    wb = Workbook()
    ws = wb.active
    ws.title = "λ 扫描"
    ws.append(header)
    for r in body:
        ws.append([float(x) for x in r])

    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = BODY_FONT
            cell.alignment = CENTER
            cell.border = BORDER

    widths = [10, 12, 14, 14, 16, 14]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=6):
        for cell in row:
            cell.number_format = "0.000" if cell.column in (2, 3, 6) else "0.00"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    ws2 = wb.create_sheet("说明")
    lines = [
        ("这份表是什么", "核心 OD（深圳北—深圳湾）在 λ = 0–2 下的路线结果，每个 λ 一行。"),
        ("怎么核对", "找 lambda = 1.0 那一行：length_km 应为 14.665，exposure_km 应为 2.727。"),
        ("λ 是什么", "暴露加价系数：边权 = 长度 × (1 + λ × 暴露)。λ 越大越愿意绕开人群。"),
        ("看什么", "λ < 1.3：长度不变、只挑等长低暴露路；λ ≥ 1.3：多走 3.2% 距离，换 17% 暴露下降。"),
        ("边界", "人口是合成数据、禁飞区是示意；结论只用于方法演示，不是安全或合规结论。"),
    ]
    ws2.append(["项目", "说明"])
    for k, v in lines:
        ws2.append([k, v])
    for cell in ws2[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
    for row in ws2.iter_rows(min_row=2):
        row[0].font = Font(name="微软雅黑", bold=True, size=10)
        for cell in row:
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = BORDER
    ws2.column_dimensions["A"].width = 16
    ws2.column_dimensions["B"].width = 78

    wb.save(OUT)
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
