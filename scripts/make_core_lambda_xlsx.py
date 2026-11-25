"""把核心 OD 的 λ 扫描结果做成一个带说明的 Excel，方便非技术读者核对。

用途：从 results/pareto.csv 里筛出核心 OD（罗湖—福田），生成
results/core_od_lambda_sweep.csv 与 .xlsx，供用户抽查 λ=1 那一行。
"""
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "pareto.csv"
CSV_OUT = ROOT / "results" / "core_od_lambda_sweep.csv"
XLSX_OUT = ROOT / "results" / "core_od_lambda_sweep.xlsx"
CORE_OD = "luohu_to_futian"

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(name="微软雅黑", bold=True, color="FFFFFF", size=10)
BODY_FONT = Font(name="微软雅黑", size=10)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center")


def load_core_rows() -> list[dict[str, str]]:
    with SRC.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["od"] == CORE_OD]
    if not rows:
        raise SystemExit(f"results/pareto.csv 里没有 {CORE_OD}，先跑 scripts/make_pareto.py")
    return rows


def main() -> None:
    rows = load_core_rows()
    header = ["lambda", "length_km", "C_proxy_m", "E", "C_change_pct", "detour_ratio"]
    body = []
    base_c = None
    for r in rows:
        c = float(r["c_proxy_km"])
        base_c = c if base_c is None else base_c
        body.append([
            float(r["lambda"]),
            float(r["length_km"]),
            c,
            c / float(r["length_km"]),
            100.0 * (c - base_c) / base_c,
            float(r["detour_ratio"]),
        ])

    with CSV_OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(body)

    wb = Workbook()
    ws = wb.active
    ws.title = "λ 扫描"
    ws.append(["λ", "长度 km", "C（代理·米）", "E = C/L", "C 变化 %", "绕行率"])
    for r in body:
        ws.append(r)

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
    for i, w in enumerate([8, 12, 14, 10, 12, 10], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=5):
        for cell in row:
            cell.number_format = "0.000" if cell.column == 4 else "0.00"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    lambdas = [r[0] for r in body]
    delta_len = [r[1] for r in body]
    c_chg = [r[4] for r in body]
    len_flat = [i for i in range(len(lambdas)) if body[i][1] == body[0][1]]
    first_len = next((i for i in range(len(lambdas)) if body[i][1] != body[0][1]), None)
    lam_first = lambdas[first_len] if first_len is not None else None
    big = len(body) - 1
    ws2 = wb.create_sheet("说明")
    lines = [
        ("这份表是什么", "核心 OD（罗湖—福田）在 λ = 0–2 下的路线结果，每个 λ 一行；C 是累计暴露（Σ边长×暴露，单位「代理·米」）。"),
        ("怎么核对", "找 λ = 1.0 那一行：长度应为 7.014 km、C 应为 4.326（代理·米），与周报一致。"),
        ("λ 是什么", "暴露加价系数：边权 = 长度 × (1 + λ × 暴露)。λ 越大越愿意绕开人群。"),
        ("看什么", f"λ<{lam_first:.3g}：长度不变（{len_flat[0] if len_flat else '—'} 档），只在等长解里挑低暴露，C 降 {abs(c_chg[0]):.1f}%；λ≈{lam_first:.3g} 起才真绕行：末尾 λ=2 时长度 +{delta_len[big] - 100:.1f}%、C 变化 {c_chg[big]:+.1f}%。"),
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
    ws2.column_dimensions["B"].width = 86

    wb.save(XLSX_OUT)
    print(f"written: {CSV_OUT}\nwritten: {XLSX_OUT}")


if __name__ == "__main__":
    main()
