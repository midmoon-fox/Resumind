"""Build only the two reference-inspired Word skeletons; existing releases stay intact."""
from pathlib import Path

from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]


def shade(element, color):
    fill = OxmlElement('w:shd')
    fill.set(qn('w:fill'), color)
    element.append(fill)


def build(key):
    document = Document()
    page = document.sections[0]
    page.page_width, page.page_height = Mm(210), Mm(297)
    page.top_margin = page.bottom_margin = Mm(15)
    page.left_margin = page.right_margin = Mm(15)
    tone = 'AAA3BE' if key == 'ribbon' else '879FB7'
    for name, size in [('Normal', 11), ('Title', 25), ('Heading 1', 12), ('Heading 2', 11)]:
        style = document.styles[name]
        style.font.name, style.font.size = 'Microsoft YaHei', Pt(size)
        style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'Microsoft YaHei')
    heading = document.styles['Heading 1'].element.get_or_add_pPr()
    borders = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    for name, value in [('val', 'single'), ('sz', '6'), ('space', '5'), ('color', tone)]:
        bottom.set(qn('w:' + name), value)
    borders.append(bottom)
    heading.append(borders)
    if key == 'ribbon':
        title = document.add_paragraph('个人简历', 'Title')
        title.runs[0].font.color.rgb = RGBColor.from_string(tone)
        document.add_paragraph('基本信息', 'Heading 1')
        host = document
    else:
        band = document.add_paragraph('● ● · ·')
        band.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        shade(band._p.get_or_add_pPr(), tone)
        table = document.add_table(rows=1, cols=2)
        table.autofit = False
        table.columns[0].width, table.columns[1].width = Mm(52), Mm(128)
        table.cell(0, 0).width, table.cell(0, 1).width = Mm(52), Mm(128)
        host = table.cell(0, 0)
        shade(host._tc.get_or_add_tcPr(), 'F0F1F2')
    for text, style in [('{{ name }}', 'Title'), ('{{ intention }}', 'Subtitle'),
                        ('{{ phone }}', 'Normal'), ('{{ email }}', 'Normal'), ('{{ age }}', 'Normal')]:
        paragraph = host.add_paragraph(text, style)
        if key == 'sidebar':
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.core_properties.title = f'Resumind {key} 1.0.0'
    document.core_properties.author = ''
    document.save(ROOT / 'assets/word' / f'{key}-1.0.0.docx')


if __name__ == '__main__':
    for key in ('ribbon', 'sidebar'):
        build(key)
