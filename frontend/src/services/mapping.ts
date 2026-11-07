import type { Schema } from './schema';
import type {
  Profile,
  ResumeDocument,
  JobDescription,
  Experience,
} from '../types/app';
import { escapeHtml, safeHtml } from '../utils/content';

export function periodText(value: {
  startDate: string | null;
  endDate: string | null;
  isCurrent: boolean;
}) {
  return [value.startDate, value.isCurrent ? '至今' : value.endDate].filter(Boolean).join(' – ');
}
export function dates(period: string) {
  if (!period.trim()) return { startDate: null, endDate: null, isCurrent: false };
  const values = [...period.matchAll(/(\d{4})[.\-/](0?[1-9]|1[0-2])(?!\d)/g)].map(
    (m) => `${m[1]}-${m[2]!.padStart(2, '0')}`,
  );
  if (!values.length || values.length > 2)
    throw new Error('时间请填写 YYYY-MM – YYYY-MM 或 YYYY-MM – 至今');
  const isCurrent = /至今|现在|current|present/i.test(period);
  if (values[1] && values[0]! > values[1]) throw new Error('结束时间不能早于开始时间');
  return { startDate: values[0]!, endDate: isCurrent ? null : (values[1] ?? null), isCurrent };
}
export function fromProfile(p: Schema<'resume_b__schemas__Profile'>): Profile {
  const e = p.education[0];
  return {
    educationFirstId: e?.id ?? crypto.randomUUID(),
    photoData: p.photoData ?? null,
    name: p.name,
    email: p.email,
    phone: p.phone ?? '',
    city: '',
    summary: '',
    school: e?.school ?? '',
    major: e?.major ?? '',
    degree: e?.degree ?? '本科',
    educationPeriod: e ? periodText(e) : '',
    skills: p.skills.join('\n'),
    skillItems: [...p.skills],
    education: JSON.parse(JSON.stringify(p.education)),
    age: p.age,
  };
}
export function toProfile(p: Profile, intention: string): Schema<'resume_b__schemas__Profile'> {
  const education = JSON.parse(
    JSON.stringify(p.education ?? []),
  ) as Schema<'resume_b__schemas__Education'>[];
  if (p.school.trim())
    education[0] = {
      id: education[0]?.id ?? (p.educationFirstId ??= crypto.randomUUID()),
      school: p.school,
      major: p.major,
      degree: p.degree,
      ...dates(p.educationPeriod),
    };
  else if (education.length) education.shift();
  return {
    photoData: p.photoData ?? null,
    name: p.name,
    phone: p.phone || null,
    email: p.email,
    intention,
    age: typeof p.age === 'number' ? p.age : null,
    education: education.map((e) => ({
      ...e,
      startDate: e.startDate || null,
      endDate: e.isCurrent ? null : e.endDate || null,
    })),
    skills:
      p.skillItems && p.skills === p.skillItems.join('\n')
        ? [...p.skillItems]
        : p.skills.trim()
          ? [p.skills.trim()]
          : [],
  };
}
type Rich = Schema<'RichNode-Output'>;
type Node = {
  type: string;
  text?: string;
  attrs?: Record<string, unknown>;
  content?: Node[];
  marks?: { type: string; attrs?: Record<string, string> }[];
};
export function richHtml(root: Rich | Node): string {
  const n = root as Node;
  if (n.type === 'text')
    return (n.marks ?? []).reduce(
      (html, m) => {
        const tag = { bold: 'strong', italic: 'em', underline: 'u' }[m.type];
        if (tag) return `<${tag}>${html}</${tag}>`;
        if (m.type === 'textStyle' && /^#[0-9a-f]{6}$/i.test(m.attrs?.color ?? ''))
          return `<span style="color:${m.attrs!.color}">${html}</span>`;
        if (m.type === 'link' && /^https?:\/\//.test(m.attrs?.href ?? ''))
          return `<a href="${escapeHtml(m.attrs!.href!)}" rel="noopener noreferrer">${html}</a>`;
        return html;
      },
      escapeHtml(n.text ?? ''),
    );
  if (n.type === 'hardBreak') return '<br>';
  const inner = (n.content ?? []).map(richHtml).join('');
  const tag = { paragraph: 'p', bulletList: 'ul', orderedList: 'ol', listItem: 'li' }[n.type];
  return tag
    ? `<${tag}${n.type === 'orderedList' ? ` start="${Number(n.attrs?.start) || 1}"` : ''}>${inner}</${tag}>`
    : inner;
}
export function htmlRich(html: string): Schema<'RichNode-Input'> {
  const dom = new DOMParser().parseFromString(safeHtml(html), 'text/html');
  function nodes(parent: globalThis.Node, marks: Node['marks'] = []): Node[] {
    return Array.from(parent.childNodes).flatMap((child): Node[] => {
      if (child.nodeType === 3)
        return child.textContent
          ? [{ type: 'text', text: child.textContent, ...(marks?.length ? { marks } : {}) }]
          : [];
      if (!(child instanceof Element)) return [];
      const tag = child.tagName.toLowerCase();
      if (tag === 'br') return [{ type: 'hardBreak' }];
      const mark = (
        { strong: 'bold', b: 'bold', em: 'italic', i: 'italic', u: 'underline' } as Record<
          string,
          string
        >
      )[tag];
      if (mark) return nodes(child, [...(marks ?? []), { type: mark }]);
      if (tag === 'a' && /^https?:\/\//.test(child.getAttribute('href') ?? ''))
        return nodes(child, [
          ...(marks ?? []),
          { type: 'link', attrs: { href: child.getAttribute('href')! } },
        ]);
      if (tag === 'span' && child instanceof HTMLElement && child.style.color) {
        const rgb = child.style.color.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
        const color = rgb
          ? '#' +
            rgb
              .slice(1)
              .map((n) => Number(n).toString(16).padStart(2, '0'))
              .join('')
              .toUpperCase()
          : child.style.color.toUpperCase();
        if (!['#333333', '#1F2937', '#2563EB', '#7661A6', '#D4A72C', '#357A5B', '#AAA3BE', '#879FB7'].includes(color))
          throw new Error('文字颜色超出后端允许范围');
        return nodes(child, [...(marks ?? []), { type: 'textStyle', attrs: { color } }]);
      }
      const type = (
        {
          p: 'paragraph',
          div: 'paragraph',
          ul: 'bulletList',
          ol: 'orderedList',
          li: 'listItem',
        } as Record<string, string>
      )[tag];
      const content = nodes(child, marks);
      if (!type) return content;
      if (type === 'listItem' && content.some((x) => x.type === 'text'))
        return [{ type, content: [{ type: 'paragraph', content }] }];
      return [
        {
          type,
          ...(type === 'orderedList'
            ? { attrs: { start: Number(child.getAttribute('start')) || 1 } }
            : {}),
          content,
        },
      ];
    });
  }
  let content = nodes(dom.body);
  if (!content.length) content = [{ type: 'paragraph', content: [] }];
  if (content.some((x) => x.type === 'text' || x.type === 'hardBreak'))
    content = [{ type: 'paragraph', content }];
  return { type: 'doc', content } as Schema<'RichNode-Input'>;
}
export function resumeCompletion(doc: ResumeDocument): {
  completeness: number;
  status: 'ready' | 'draft';
} {
  const checks = [
    doc.profile.name.trim(),
    doc.profile.email.trim() || doc.profile.phone.trim(),
    doc.role.trim(),
    doc.profile.school.trim(),
    doc.profile.skills.trim(),
    doc.sections.some((s) => !s.hidden && s.items.some((i) => i.title.trim())),
  ];
  const completeness = Math.round((checks.filter(Boolean).length / checks.length) * 100);
  return { completeness, status: completeness === 100 ? 'ready' : 'draft' };
}
export function fromResume(r: Schema<'ResumeOutput'>): ResumeDocument {
  const doc: ResumeDocument = {
    backend: r,
    id: r.id,
    title: r.title,
    role: r.document.profile.intention,
    template: r.templateId as ResumeDocument['template'],
    status: 'draft',
    updatedAt: r.updatedAt,
    completeness: 0,
    revision: r.revision,
    profile: fromProfile(r.document.profile),
    style: {
      accent: r.style.accentColor,
      font: r.style.fontFamily,
      fontSize: r.style.fontSize,
      lineHeight: r.style.lineHeight,
      sectionGap: r.style.sectionGap,
    },
    sections: r.document.sections.map((s) => ({
      id: s.id,
      title: s.title,
      kind: s.type,
      hidden: !s.visible,
      items: s.items.map((i) => ({
        id: i.id,
        title: i.title,
        subtitle: i.subtitle,
        period: periodText(i),
        html: richHtml(i.description),
      })),
      chartData: s.chartData ?? undefined,
      links: s.links ?? undefined,
      text: s.text ? richHtml(s.text) : undefined,
    })),
  };
  return Object.assign(doc, resumeCompletion(doc));
}
export function toDocument(r: ResumeDocument): Schema<'Document-Input'> {
  return {
    schemaVersion: '1.0.0',
    profile: toProfile(r.profile, r.role),
    sections: r.sections.map((s) => ({
      id: s.id,
      title: s.title,
      type: s.kind as Schema<'Section-Input'>['type'],
      visible: !s.hidden,
      items: (['EDUCATION', 'SKILLS', 'CHARTS', 'SOCIAL_LINKS', 'TEXT'].includes(s.kind)
        ? []
        : s.items
      ).map((i) => {
        const original = r.backend?.document.sections
          .flatMap((x) => x.items)
          .find((x) => x.id === i.id);
        return {
          id: i.id,
          title: i.title,
          subtitle: i.subtitle,
          ...dates(i.period),
          description:
            original && richHtml(original.description) === i.html
              ? original.description
              : htmlRich(i.html),
          experienceId: original?.experienceId ?? null,
          sourceRevision: original?.sourceRevision ?? null,
        };
      }),
      chartData: s.kind === 'CHARTS' ? (s.chartData ?? [{ label: '', value: 0, unit: '' }]) : null,
      links:
        s.kind === 'SOCIAL_LINKS'
          ? (s.links ?? []).filter(
              (link) => link.platform.trim() || link.label.trim() || link.url.trim(),
            )
          : null,
      text: s.kind === 'TEXT' ? (s.text ? htmlRich(s.text) : htmlRich('<p></p>')) : null,
    })),
  };
}
export function toStyle(r: ResumeDocument): Schema<'Style'> {
  return {
    fontFamily: r.style.font as Schema<'Style'>['fontFamily'],
    fontSize: Number(r.style.fontSize),
    lineHeight: Number(r.style.lineHeight),
    accentColor: r.style.accent as Schema<'Style'>['accentColor'],
    sectionGap: Number(r.style.sectionGap),
  };
}
export function fromJd(j: Schema<'JdOut'>, v: Schema<'JdVersionOut'>): JobDescription {
  return {
    backend: j,
    version: v,
    id: j.id,
    title: j.title,
    company: v.companyName ?? '',
    city: '',
    text: v.originalText,
    tags: v.requirements.map((r) => r.text),
    createdAt: j.createdAt,
    source: 'manual',
  };
}
const experienceTypes = {
  PROJECT: '项目经历',
  INTERNSHIP: '实习经历',
  CAMPUS: '校园经历',
  AWARD: '获奖经历',
};
export function fromExperience(e: Schema<'ExperienceOut'>): Experience {
  return {
    backend: e,
    id: e.id,
    type: experienceTypes[e.type],
    title: e.data.name,
    role: e.data.personalRole,
    period: periodText(e.data),
    description: [
      ...(e.data.background ? ['背景：' + e.data.background] : []),
      ...e.data.actions.map((x) => '行动：' + x),
      ...e.data.outcomes.map((x) => '结果：' + x),
      ...(e.data.technologies.length ? ['技术：' + e.data.technologies.join('、')] : []),
    ].join('\n'),
    confirmed: e.status === 'CONFIRMED',
    excluded: e.excluded,
  };
}
export function experienceData(e: Experience): Schema<'app__schemas__ExperienceData'> {
  const lines = e.description.split('\n').filter((x) => x.trim());
  const pick = (label: string) =>
    lines.filter((x) => x.startsWith(label + '：')).map((x) => x.slice(label.length + 1));
  const plain = lines.filter((x) => !/^(背景|行动|结果|技术)：/.test(x));
  return {
    name: e.title,
    personalRole: e.role,
    ...dates(e.period),
    background: pick('背景').join('\n'),
    actions: [...pick('行动'), ...plain],
    outcomes: pick('结果'),
    technologies: pick('技术')
      .join('、')
      .split(/[、,，]/)
      .filter(Boolean),
  };
}
export function experienceType(type: string): Schema<'ExperienceOut'>['type'] {
  const entry = Object.entries(experienceTypes).find(([, name]) => name === type);
  if (!entry) throw new Error('请选择后端支持的经历类型');
  return entry[0] as Schema<'ExperienceOut'>['type'];
}

export function mergeSources(
  data: Schema<'app__schemas__ExperienceData'>,
  sources: Schema<'ExperienceOut'>[],
): Schema<'SourceMapping'>[] {
  function leaves(value: unknown, path = ''): [string, unknown][] {
    if (value && typeof value === 'object')
      return Object.entries(value).flatMap(([k, v]) => leaves(v, path + '/' + k));
    return value === null || value === '' ? [] : [[path, value]];
  }
  const original = sources.flatMap((e) =>
    leaves(e.data).map(([jsonPointer, value]) => ({ experienceId: e.id, jsonPointer, value })),
  );
  return leaves(data).flatMap(([jsonPointer, value]) => {
    const matches = original
      .filter(
        (s) =>
          s.value === value &&
          s.jsonPointer.replace(/\/\d+/g, '/*') === jsonPointer.replace(/\/\d+/g, '/*'),
      )
      .map(({ experienceId, jsonPointer }) => ({ experienceId, jsonPointer }));
    return matches.length ? [{ jsonPointer, sources: matches }] : [];
  });
}
