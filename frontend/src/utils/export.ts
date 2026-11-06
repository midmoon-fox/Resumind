import { h, render } from 'vue';
import ResumeDocumentView from '../components/resume/ResumeDocument.vue';
import documentCss from '../styles/resume.css?inline';
import type { ResumeDocument } from '../types/app';
import { downloadBlob, escapeHtml, safeHtml } from './content';

export function exportIssues(doc: ResumeDocument) {
  const issues: string[] = [];
  if (!doc.profile.name.trim()) issues.push('请填写姓名');
  if (!doc.profile.email.trim() && !doc.profile.phone.trim())
    issues.push('请至少填写邮箱或手机号码');
  if (!doc.role.trim() || doc.role === '待填写方向') issues.push('请填写求职方向');
  if (doc.profile.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(doc.profile.email))
    issues.push('邮箱格式不正确');
  return issues;
}
function htmlDocument(doc: ResumeDocument, title = doc.title) {
  const node = document.createElement('div');
  render(h(ResumeDocumentView, { document: doc }), node);
  const html = node.innerHTML;
  render(null, node);
  return (
    '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' +
    escapeHtml(title) +
    '</title><style>' +
    documentCss +
    '</style></head><body>' +
    html +
    '</body></html>'
  );
}
export function exportHtml(doc: ResumeDocument, filename: string) {
  downloadBlob(
    new Blob([htmlDocument(doc, filename)], { type: 'text/html;charset=utf-8' }),
    filename + '.html',
  );
}
export function printResume(doc: ResumeDocument, filename = doc.title) {
  const popup = window.open('', '_blank');
  if (!popup) return false;
  popup.opener = null;
  popup.document.open();
  popup.document.write(htmlDocument(doc, filename));
  popup.document.close();
  void popup.document.fonts.ready.then(() => {
    popup.focus();
    popup.print();
  });
  return true;
}
export async function exportWord(doc: ResumeDocument, filename: string) {
  const { Document, Packer, Paragraph, TextRun, HeadingLevel } = await import('docx');
  const font = doc.style.font;
  const accent = doc.style.accent.replace('#', '');
  const paragraphs = [
    new Paragraph({ text: doc.profile.name, heading: HeadingLevel.TITLE }),
    new Paragraph({ text: doc.role }),
    new Paragraph({
      text: [doc.profile.phone, doc.profile.email, doc.profile.city].filter(Boolean).join(' · '),
    }),
  ];
  const heading = (text: string) =>
    paragraphs.push(new Paragraph({ text, heading: HeadingLevel.HEADING_1 }));
  if (doc.profile.summary) {
    heading('个人简介');
    paragraphs.push(new Paragraph(doc.profile.summary));
  }
  if (doc.profile.school) {
    heading('教育背景');
    paragraphs.push(
      new Paragraph(doc.profile.school + '   ' + doc.profile.educationPeriod),
      new Paragraph(doc.profile.major + ' · ' + doc.profile.degree),
    );
  }
  for (const section of doc.sections.filter((s) => !s.hidden)) {
    heading(section.title);
    for (const item of section.items) {
      paragraphs.push(
        new Paragraph({
          children: [
            new TextRun({ text: item.title, bold: true }),
            new TextRun('   ' + item.period),
          ],
        }),
      );
      if (item.subtitle) paragraphs.push(new Paragraph(item.subtitle));
      const root = document.createElement('div');
      root.innerHTML = safeHtml(item.html);
      const blocks = Array.from(root.querySelectorAll('p, li')).filter(
        (el) => !el.closest('li') || el.tagName === 'LI',
      );
      for (const block of blocks) {
        const runs: InstanceType<typeof TextRun>[] = [];
        if (block.parentElement?.tagName === 'OL')
          runs.push(
            new TextRun(Array.from(block.parentElement!.children).indexOf(block) + 1 + '. '),
          );
        function walk(
          node: Node,
          marks: { bold?: boolean; italics?: boolean; underline?: boolean; color?: string } = {},
        ) {
          if (node.nodeType === Node.TEXT_NODE) {
            runs.push(
              new TextRun({
                text: node.textContent || '',
                ...marks,
                underline: marks.underline ? {} : undefined,
              }),
            );
            return;
          }
          if (node instanceof HTMLElement) {
            if (node.tagName === 'UL' || node.tagName === 'OL') return;
            const next = { ...marks };
            if (node.tagName === 'STRONG') next.bold = true;
            if (node.tagName === 'EM') next.italics = true;
            if (node.tagName === 'U') next.underline = true;
            if (node.style.color) {
              const c = node.style.color.match(/\d+/g);
              if (c && c.length === 3)
                next.color = c.map((v) => Number(v).toString(16).padStart(2, '0')).join('');
            }
            if (node.tagName === 'BR') runs.push(new TextRun({ break: 1 }));
            node.childNodes.forEach((child) => walk(child, next));
          }
        }
        block.childNodes.forEach((node) => walk(node));
        paragraphs.push(
          new Paragraph({
            children: runs,
            bullet: block.parentElement?.tagName === 'UL' ? { level: 0 } : undefined,
          }),
        );
      }
    }
  }
  if (doc.profile.skills) {
    heading('专业技能');
    paragraphs.push(new Paragraph(doc.profile.skills));
  }
  const wordDocument = new Document({
    styles: {
      default: {
        document: {
          run: { font, size: doc.style.fontSize * 2 },
          paragraph: { spacing: { after: 120, line: Math.round(doc.style.lineHeight * 240) } },
        },
      },
      paragraphStyles: [
        {
          id: 'Heading1',
          name: 'Heading 1',
          basedOn: 'Normal',
          next: 'Normal',
          quickFormat: true,
          run: { color: accent, bold: true, size: 26 },
          paragraph: { spacing: { before: 240, after: 120 } },
        },
      ],
    },
    sections: [
      {
        properties: {
          page: {
            size: { width: 11906, height: 16838 },
            margin: { top: 1000, right: 1000, bottom: 1000, left: 1000 },
          },
        },
        children: paragraphs,
      },
    ],
  });
  downloadBlob(await Packer.toBlob(wordDocument), filename + '.docx');
}
