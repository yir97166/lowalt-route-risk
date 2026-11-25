"""md-to-word 导出后的收尾：作者块居中（作者加粗），其余不动。"""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOCX = Path(__file__).resolve().parents[1] / "report" / "低空航路规划原型-技术报告-v1.0.docx"
PREFIXES = ("弋昊阳", "中国民航大学", "College of", "联系邮箱", "技术报告 v1.0")


def main() -> None:
    doc = Document(DOCX)
    for para in doc.paragraphs[:10]:
        text = para.text.strip()
        if not text.startswith(PREFIXES):
            continue
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.italic = False
            if text.startswith("弋昊阳"):
                run.bold = True
    doc.save(DOCX)
    print(f"finalized {DOCX.name}")


if __name__ == "__main__":
    main()
