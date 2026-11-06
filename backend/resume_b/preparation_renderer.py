"""Preparation documents use a separate document layout, never resume templates."""
import hashlib
from html import escape
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from .documents import require
from .preparation_content import validate_content
from .preflight import PreflightFailed, PreflightUnavailable
from .content_check import missing_text_paths


def preparation_blocks(snapshot):
    validate_content(snapshot["content"], snapshot["type"])
    content = snapshot["content"]
    if snapshot["type"] == "INTRODUCTION":
        return [("title", "面试自我介绍"), ("body", content["introduction"])]
    blocks = [("title", "面试问题与参考回答")]
    for question in content["questions"]:
        blocks.extend([("heading", f"{question['number']} {question['question']}"), ("label", "参考回答"), ("body", question["referenceAnswer"])])
        if question["missingFacts"]:
            blocks.append(("label", "待补充事实"))
            blocks.extend(("body", fact) for fact in question["missingFacts"])
    return blocks


def check_text(text, blocks):
    if missing_text_paths(text, [("/content", value) for _, value in blocks]):
        raise PreflightFailed([{"code": "CONTENT_MISSING", "severity": "ERROR", "path": "/content", "message": "导出文件缺少准备资料正文"}])


class PreparationRenderer:
    def __init__(self, *, docx_template_loader, pdf_font_file, subfont_index=0):
        self.docx_template_loader = docx_template_loader
        self.pdf_font_file = Path(pdf_font_file)
        self.subfont_index = subfont_index

    def render(self, snapshot):
        require(snapshot["format"] in {"PDF", "DOCX"}, "/format", "preparation format must be PDF or DOCX")
        blocks = preparation_blocks(snapshot)
        return self.pdf(blocks) if snapshot["format"] == "PDF" else self.docx(blocks)

    def docx(self, blocks):
        from docx import Document
        from docx.shared import Pt, RGBColor
        document = Document(BytesIO(self.docx_template_loader()))
        for kind, value in blocks:
            style = {"title": "Title", "heading": "Heading 1", "label": "Heading 2", "body": "Normal"}[kind]
            # Split explicit user newlines without evaluating any markup or template syntax.
            lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            for line in lines:
                paragraph = document.add_paragraph(line, style)
                if kind != "body":
                    paragraph.paragraph_format.keep_with_next = True
        document.styles["Title"].font.color.rgb = RGBColor(0, 0, 0)
        document.styles["Normal"].font.size = Pt(12)
        output = BytesIO()
        document.save(output)
        data = output.getvalue()
        with ZipFile(BytesIO(data)) as archive:
            from lxml import etree
            check_text("".join(etree.fromstring(archive.read("word/document.xml")).itertext()), blocks)
        Document(BytesIO(data))
        return data

    def pdf(self, blocks):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate
        from pypdf import PdfReader
        if not self.pdf_font_file.is_file():
            raise PreflightUnavailable("configured preparation font asset is unavailable")
        name = "Preparation" + hashlib.sha256(self.pdf_font_file.read_bytes()).hexdigest()[:16] + str(self.subfont_index)
        try:
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(self.pdf_font_file), subfontIndex=self.subfont_index))
            face = pdfmetrics.getFont(name).face
            if any(ord(char) not in face.charToGlyph for _, text in blocks for char in text if not char.isspace()):
                raise PreflightUnavailable("configured font does not cover preparation content")
        except PreflightUnavailable:
            raise
        except Exception as error:
            raise PreflightUnavailable("configured preparation font could not be loaded") from error
        styles = {
            "title": ParagraphStyle("title", fontName=name, fontSize=20, leading=28, textColor=colors.black, spaceAfter=18, keepWithNext=True, wordWrap="CJK"),
            "heading": ParagraphStyle("heading", fontName=name, fontSize=14, leading=21, textColor=colors.HexColor("#1F2937"), spaceBefore=14, spaceAfter=6, keepWithNext=True, wordWrap="CJK"),
            "label": ParagraphStyle("label", fontName=name, fontSize=11, leading=18, textColor=colors.HexColor("#555555"), spaceBefore=6, spaceAfter=4, keepWithNext=True, wordWrap="CJK"),
            "body": ParagraphStyle("body", fontName=name, fontSize=12, leading=20, textColor=colors.HexColor("#333333"), spaceAfter=8, wordWrap="CJK", splitLongWords=True),
        }
        story = [Paragraph(escape(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>"), styles[kind]) for kind, text in blocks if text.strip()]
        output = BytesIO()
        SimpleDocTemplate(output, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                          title=blocks[0][1], author="").build(story)
        data = output.getvalue()
        reader = PdfReader(BytesIO(data), strict=True)
        check_text("".join(page.extract_text() or "" for page in reader.pages), blocks)
        for page in reader.pages:
            if abs(float(page.mediabox.width) - A4[0]) > 2 or abs(float(page.mediabox.height) - A4[1]) > 2:
                raise PreflightUnavailable("preparation PDF is not portrait A4")
        return data
