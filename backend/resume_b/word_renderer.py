from .visibility import section_has_content, item_has_content
"""Versioned docxtpl skeleton plus editable OOXML content mapping."""
from io import BytesIO
import base64
from zipfile import ZipFile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.shared import Pt, RGBColor
from docxtpl import DocxTemplate
from jinja2 import Environment, StrictUndefined
from lxml import etree

from .documents import validate_document, validate_style, validate_template
from .pdf_renderer import expected_text
from .preflight import PreflightUnavailable, PreflightFailed
from .content_check import missing_text_paths


class WordRenderer:
    def __init__(self, template_loader):
        self.template_loader = template_loader

    def render(self, snapshot):
        document, style = snapshot["document"], snapshot["style"]
        validate_document(document)
        validate_style(style)
        validate_template(snapshot["templateId"], snapshot["templateVersion"])
        template = DocxTemplate(BytesIO(self.template_loader(snapshot["templateId"], snapshot["templateVersion"])))
        profile = document["profile"]
        context = {key: profile[key] or "" for key in ("name", "phone", "email", "intention")}
        context["age"] = "" if profile["age"] is None else f"{profile['age']}岁"
        template.render(context, jinja_env=Environment(undefined=StrictUndefined), autoescape=True)
        stream = BytesIO()
        template.save(stream)
        output = Document(BytesIO(stream.getvalue()))
        body = output.tables[0].cell(0, 1) if snapshot['templateId'] == 'sidebar' else output
        if profile.get('photoData'):
            photo_host = output.tables[0].cell(0, 0) if snapshot['templateId'] == 'sidebar' else output
            paragraph = photo_host.paragraphs[0] if photo_host.paragraphs else photo_host.add_paragraph()
            paragraph.add_run().add_picture(BytesIO(base64.b64decode(profile['photoData'].split(',', 1)[1])), width=Pt(58), height=Pt(78))
        normal = output.styles["Normal"]
        normal.font.name = style["fontFamily"]
        normal.font.size = Pt(style["fontSize"])
        normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), style["fontFamily"])
        normal.paragraph_format.line_spacing = style["lineHeight"]
        normal.paragraph_format.space_after = Pt(4)
        # Explicitly map all template/global font settings, including heading East Asian fonts.
        for heading in ("Title", "Heading 1", "Heading 2"):
            font = output.styles[heading].font
            font.name = style["fontFamily"]
            output.styles[heading].element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), style["fontFamily"])
            font.color.rgb = RGBColor.from_string("000000" if heading == "Title" else style["accentColor"][1:])
        # Every colored template rule follows the same editable accent as HTML/PDF.
        for border in output.styles['Heading 1'].element.iter(qn('w:bottom')):
            border.set(qn('w:color'), style['accentColor'][1:])
        theme = {'ribbon': 'AAA3BE', 'sidebar': '879FB7'}.get(snapshot['templateId'])
        if theme:
            output.styles['Heading 1'].font.color.rgb = RGBColor.from_string(theme)
            for border in output.styles['Heading 1'].element.iter(qn('w:bottom')):
                border.set(qn('w:color'), theme)
        mapper = RichTextMapper(body, style)
        for section in document["sections"]:
            if not section_has_content(section, profile):
                continue
            heading = body.add_paragraph(section["title"], "Heading 1")
            heading.paragraph_format.space_before = Pt(style["sectionGap"] * 0.75)
            heading.paragraph_format.keep_with_next = True
            if section["type"] == "EDUCATION":
                for education in profile["education"]:
                    body.add_paragraph(" / ".join(filter(None, (education["school"], education["major"], education["degree"]))))
                    body.add_paragraph(date_label(education))
            elif section["type"] == "SKILLS":
                if profile["skills"]:
                    body.add_paragraph("\n".join(profile["skills"]))
            elif section["type"] == "TEXT":
                mapper.blocks(section["text"].get("content", []))
            elif section["type"] == "SOCIAL_LINKS":
                for link in section["links"]:
                    body.add_paragraph(" · ".join(filter(None, (link["platform"], link["label"], link["url"]))))
            elif section["type"] == "CHARTS":
                for datum in section["chartData"]:
                    body.add_paragraph(f'{datum["label"]} {datum["value"]} {datum["unit"] or ""}')
            else:
                for item in section["items"]:
                    if not item_has_content(item):
                        continue
                    title = body.add_paragraph(item["title"], "Heading 2")
                    title.paragraph_format.keep_with_next = True
                    if snapshot['templateId'] == 'project' and section['type'] == 'PROJECTS':
                        for paragraph in (title,):
                            borders = OxmlElement('w:pBdr')
                            left = OxmlElement('w:left')
                            for name, value in [('val','single'), ('sz','12'), ('space','8'), ('color',style['accentColor'][1:])]:
                                left.set(qn('w:' + name), value)
                            borders.append(left)
                            paragraph._p.get_or_add_pPr().append(borders)
                    subtitle = " / ".join(filter(None, (item["subtitle"], date_label(item))))
                    if subtitle:
                        body.add_paragraph(subtitle)
                    mapper.blocks(item["description"].get("content", []))
        result = BytesIO()
        output.save(result)
        data = result.getvalue()
        validate_docx(data, document)
        return data

    def inspect(self, snapshot, format):
        if format != "DOCX":
            raise PreflightUnavailable("Word inspector only handles DOCX")
        self.render(snapshot)
        return {"completed": True, "issues": []}


def date_label(record):
    start = record["startDate"] or ""
    end = "至今" if record["isCurrent"] else record["endDate"] or ""
    return " - ".join(value for value in (start, end) if value)


class RichTextMapper:
    def __init__(self, document, style):
        self.document, self.style = document, style

    def list_number(self, kind, start, depth):
        root = self.document.part.numbering_part.element
        abstract_id = max([int(node.get(qn("w:abstractNumId"))) for node in root.findall(qn("w:abstractNum"))] + [-1]) + 1
        num_id = max([int(node.get(qn("w:numId"))) for node in root.findall(qn("w:num"))] + [0]) + 1
        abstract = OxmlElement("w:abstractNum")
        abstract.set(qn("w:abstractNumId"), str(abstract_id))
        level = OxmlElement("w:lvl")
        level.set(qn("w:ilvl"), "0")
        for tag, value in (("start", str(start)), ("numFmt", "decimal" if kind == "orderedList" else "bullet"), ("lvlText", "%1." if kind == "orderedList" else "•"), ("lvlJc", "left")):
            element = OxmlElement("w:" + tag)
            element.set(qn("w:val"), value)
            level.append(element)
        properties = OxmlElement("w:pPr")
        indent = OxmlElement("w:ind")
        indent.set(qn("w:left"), str(360 * (depth + 1)))
        indent.set(qn("w:hanging"), "180")
        properties.append(indent)
        level.append(properties)
        abstract.append(level)
        # Word schema requires abstractNum definitions before concrete num entries.
        first_num = root.find(qn("w:num"))
        if first_num is not None:
            first_num.addprevious(abstract)
        else:
            root.append(abstract)
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(num_id))
        reference = OxmlElement("w:abstractNumId")
        reference.set(qn("w:val"), str(abstract_id))
        num.append(reference)
        root.append(num)
        return num_id

    def number(self, paragraph, num_id):
        properties = paragraph._p.get_or_add_pPr()
        numbering = OxmlElement("w:numPr")
        for tag, value in (("ilvl", "0"), ("numId", str(num_id))):
            element = OxmlElement("w:" + tag)
            element.set(qn("w:val"), value)
            numbering.append(element)
        properties.append(numbering)

    def inline(self, paragraph, nodes):
        for node in nodes:
            if node["type"] == "hardBreak":
                paragraph.add_run().add_break()
                continue
            run = paragraph.add_run(node["text"])
            hyperlink = None
            for mark in node.get("marks", []):
                if mark["type"] in {"bold", "italic", "underline"}:
                    setattr(run, mark["type"], True)
                elif mark["type"] == "textStyle":
                    run.font.color.rgb = RGBColor.from_string(mark["attrs"]["color"][1:])
                elif mark["type"] == "link":
                    hyperlink = mark["attrs"]["href"]
            if hyperlink:
                element = OxmlElement("w:hyperlink")
                element.set(qn("r:id"), paragraph.part.relate_to(hyperlink, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
                paragraph._p.remove(run._r)
                element.append(run._r)
                paragraph._p.append(element)

    def blocks(self, nodes, depth=0):
        for node in nodes:
            if node["type"] == "paragraph":
                paragraph = self.document.add_paragraph()
                if depth:
                    paragraph.paragraph_format.left_indent = Pt(18 * depth)
                self.inline(paragraph, node.get("content", []))
            elif node["type"] in {"bulletList", "orderedList"}:
                num_id = self.list_number(node["type"], node.get("attrs", {}).get("start", 1), depth)
                for item in node["content"]:
                    first, *rest = item["content"]
                    paragraph = self.document.add_paragraph()
                    self.number(paragraph, num_id)
                    self.inline(paragraph, first.get("content", []))
                    self.blocks(rest, depth + 1)


def validate_docx(data, document):
    with ZipFile(BytesIO(data)) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
        text = "".join(root.itertext())
        # Whitespace may change across Word runs; never accept silent text omission.
        missing = [{"code": "CONTENT_MISSING", "severity": "ERROR", "path": path, "message": "Word 缺少应显示的正文"} for path in missing_text_paths(text, expected_text(document))]
        if missing:
            raise PreflightFailed(missing)
        if root.find(".//" + qn("w:sectPr")) is None:
            raise PreflightUnavailable("Word document has no page definition")
    Document(BytesIO(data))
