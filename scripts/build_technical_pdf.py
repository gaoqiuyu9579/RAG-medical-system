"""从评审 Markdown 生成带中文字体、图表和分页的技术 PDF。"""

import re
from html import escape
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "评审技术文档.md"
DESTINATION = ROOT / "output" / "pdf" / "智慧医疗系统技术文档.pdf"
NAVY = colors.HexColor("#122B42")
TEAL = colors.HexColor("#087E8B")
BODY = "ChineseBody"
HEADING = "ChineseHeading"


def register_fonts():
    regular = Path("C:/Windows/Fonts/simsun.ttc")
    bold = Path("C:/Windows/Fonts/simhei.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont(BODY, str(regular), subfontIndex=0))
        pdfmetrics.registerFont(TTFont(HEADING, str(bold)))
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        pdfmetrics.registerFontFamily("STSong-Light", normal="STSong-Light", bold="STSong-Light")
        return "STSong-Light", "STSong-Light"
    pdfmetrics.registerFontFamily(BODY, normal=BODY, bold=HEADING, italic=BODY, boldItalic=HEADING)
    return BODY, HEADING


def diagram():
    image = PILImage.new("RGB", (1600, 700), "#f4f8fb")
    draw = ImageDraw.Draw(image)
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    if not font_path.exists():
        # Linux 重建时保留仓库已生成的图；也可安装中文字体后改此路径。
        existing = ROOT / "docs/assets/architecture.png"
        if existing.exists():
            return
        raise FileNotFoundError("生成架构图需要中文字体，或使用仓库中的 architecture.png")
    font = ImageFont.truetype(str(font_path), 30)
    small = ImageFont.truetype(str(font_path), 24)

    def box(rect, lines, fill="#ffffff", outline="#cbdde7"):
        draw.rounded_rectangle(rect, radius=20, fill=fill, outline=outline, width=3)
        center = (rect[0] + rect[2]) / 2
        y = (rect[1] + rect[3] - len(lines) * 43) / 2
        for line in lines:
            bounds = draw.textbbox((0, 0), line, font=font)
            draw.text((center - (bounds[2] - bounds[0]) / 2, y), line, font=font, fill="#15354c")
            y += 43

    def arrow(start, end):
        draw.line([start, end], fill="#087e8b", width=5)
        x, y = end
        draw.polygon([(x, y), (x - 14, y - 9), (x - 14, y + 9)], fill="#087e8b")

    box((45, 235, 350, 420), ["浏览器", "Vue 3 / Element Plus"])
    box((450, 210, 830, 450), ["Flask / Waitress", "控制器 · 服务 · 鉴权"])
    box((1000, 45, 1550, 190), ["MySQL 8.0", "用户 · 患者 · 病历"])
    box((1000, 255, 1550, 400), ["本地 Chroma", "知识片段 · 向量 · 来源"])
    box((1000, 465, 1550, 635), ["外部 AI 兼容接口", "向量模型 + 对话模型"])
    arrow((350, 325), (450, 325))
    for y in (118, 328, 550):
        draw.line([(830, 328), (910, 328), (910, y)], fill="#087e8b", width=5)
        arrow((910, y), (1000, y))
    draw.text(
        (55, 615),
        "开发：Vite 5173 → API 5000    部署：主机 8080 → 应用 5000",
        font=small,
        fill="#486579",
    )
    path = ROOT / "docs/assets/architecture.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def inline(text):
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" color="#087E8B">\1</a>', text)


def main():
    body_font, heading_font = register_fonts()
    diagram()
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    styles = {
        "body": ParagraphStyle(
            "Body",
            fontName=body_font,
            fontSize=10,
            leading=17,
            spaceAfter=8,
            wordWrap="CJK",
            textColor=NAVY,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName=heading_font,
            fontSize=19,
            leading=26,
            spaceBefore=3,
            spaceAfter=16,
            textColor=NAVY,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            fontName=heading_font,
            fontSize=12,
            leading=18,
            spaceBefore=9,
            spaceAfter=7,
            textColor=TEAL,
            keepWithNext=True,
        ),
        "cell": ParagraphStyle(
            "Cell", fontName=body_font, fontSize=8.6, leading=13.5, wordWrap="CJK", textColor=NAVY
        ),
        "th": ParagraphStyle(
            "TH",
            fontName=heading_font,
            fontSize=8.8,
            leading=14,
            wordWrap="CJK",
            textColor=colors.white,
        ),
    }
    content_width = A4[0] - 36 * mm
    story = [Spacer(1, 30 * mm)]
    cover = ParagraphStyle(
        "Cover", fontName=heading_font, fontSize=32, leading=47, textColor=NAVY, alignment=TA_LEFT
    )
    story.extend(
        [
            Paragraph("智慧医疗系统<br/>技术文档", cover),
            Spacer(1, 8 * mm),
            Paragraph("RAG 医疗系统 / 评审交付版", styles["h3"]),
            Spacer(1, 9 * mm),
            Paragraph("患者信息管理 · 电子病历 · 可追溯知识问答", styles["body"]),
            Paragraph("Vue 3 + Flask + MySQL + Chroma", styles["body"]),
            Spacer(1, 22 * mm),
            Paragraph("项目负责人：高秋雨", styles["body"]),
            Paragraph("项目成员：高秋雨、栾子璇、郝崇泽", styles["body"]),
            Paragraph("版本：3.0  |  日期：2026-10-22", styles["body"]),
            Paragraph("代码托管：GitHub / gaoqiuyu9579 / RAG-medical-system", styles["body"]),
            Spacer(1, 12 * mm),
            Paragraph(
                "项目原型与合成资料用于教学评审；AI 回答需核对来源，不能替代医生诊断。",
                styles["body"],
            ),
            PageBreak(),
        ]
    )
    lines = SOURCE.read_text(encoding="utf-8").splitlines()[4:]
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line == "<!-- pagebreak -->":
            story.append(PageBreak())
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["h2"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), styles["h3"]))
        elif line.startswith("!["):
            match = re.match(r"!\[([^]]+)\]\(([^)]+)\)", line)
            image_path = SOURCE.parent / match[2]
            with PILImage.open(image_path) as original:
                width, height = original.size
            rendered_height = content_width * height / width
            story.append(
                KeepTogether(
                    [
                        Image(str(image_path), width=content_width, height=rendered_height),
                        Spacer(1, 4),
                        Paragraph(
                            match[1],
                            ParagraphStyle("Caption", parent=styles["cell"], alignment=TA_CENTER),
                        ),
                        Spacer(1, 8),
                    ]
                )
            )
        elif line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    rows.append(cells)
                index += 1
            count = len(rows[0])
            ratios = {2: [0.30, 0.70], 3: [0.22, 0.35, 0.43]}.get(count, [1 / count] * count)
            data = [
                [
                    Paragraph(inline(cell), styles["th"] if r == 0 else styles["cell"])
                    for cell in row
                ]
                for r, row in enumerate(rows)
            ]
            table = Table(
                data,
                colWidths=[content_width * ratio for ratio in ratios],
                repeatRows=1,
                hAlign="LEFT",
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.HexColor("#F0F5F8"), colors.white],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("LINEBELOW", (0, 0), (-1, 0), 1, TEAL),
                        ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#D7E3EA")),
                    ]
                )
            )
            story.extend([table, Spacer(1, 10)])
            continue
        else:
            paragraph = line
            while (
                index + 1 < len(lines)
                and lines[index + 1].strip()
                and not lines[index + 1].startswith(("#", "|", "![", "<!--"))
            ):
                index += 1
                paragraph += " " + lines[index].strip()
            story.append(Paragraph(inline(paragraph), styles["body"]))
        index += 1

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(TEAL)
        canvas.setLineWidth(1)
        canvas.line(18 * mm, 281 * mm, A4[0] - 18 * mm, 281 * mm)
        canvas.setFont(heading_font, 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(18 * mm, 284 * mm, "RAG 医疗系统 / 技术文档")
        canvas.setFont(body_font, 8)
        canvas.drawString(18 * mm, 12 * mm, "评审交付版  |  2026-10-22")
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, str(doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(DESTINATION),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=23 * mm,
        bottomMargin=22 * mm,
        title="智慧医疗系统技术文档",
        author="高秋雨、栾子璇、郝崇泽",
    )
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    reader = PdfReader(DESTINATION)
    if len(reader.pages) > 30:
        raise ValueError(f"PDF exceeds the page limit: {len(reader.pages)}")
    print(f"PDF generated: {len(reader.pages)} pages, {DESTINATION.stat().st_size} bytes")


if __name__ == "__main__":
    main()
