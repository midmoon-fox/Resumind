export interface SectionDefinition {
  type: string;
  title: string;
  category: string;
  allowItems: boolean;
  shape?: 'items' | 'chart' | 'links' | 'text';
}

export const sectionRegistry: SectionDefinition[] = [
  { type: 'ACHIEVEMENTS', title: '成就', category: '内容模块', allowItems: true },
  { type: 'AWARDS', title: '奖项', category: '内容模块', allowItems: true },
  { type: 'CERTIFICATES', title: '证书', category: '内容模块', allowItems: true },
  { type: 'EDUCATION', title: '教育经历', category: '基础信息', allowItems: false },
  { type: 'GOAL', title: '目标', category: '内容模块', allowItems: true },
  { type: 'CHARTS', title: '图表', category: '内容模块', allowItems: false, shape: 'chart' },
  { type: 'HOBBIES', title: '爱好', category: '内容模块', allowItems: true },
  { type: 'PROJECTS', title: '项目经历', category: '内容模块', allowItems: true },
  { type: 'PUBLICATIONS', title: '发表作品', category: '内容模块', allowItems: true },
  { type: 'REFERENCES', title: '推荐人', category: '内容模块', allowItems: true },
  { type: 'SKILLS', title: '技能', category: '基础信息', allowItems: false },
  {
    type: 'SOCIAL_LINKS',
    title: '社交媒体',
    category: '内容模块',
    allowItems: false,
    shape: 'links',
  },
  { type: 'STRENGTHS', title: '优势', category: '内容模块', allowItems: true },
  { type: 'VOLUNTEERING', title: '志愿服务', category: '内容模块', allowItems: true },
  { type: 'WORK_EXPERIENCE', title: '工作经验', category: '内容模块', allowItems: true },
  { type: 'INTERNSHIPS', title: '实习经历', category: '内容模块', allowItems: true },
  { type: 'CAMPUS', title: '校园经历', category: '内容模块', allowItems: true },
  { type: 'TEXT', title: '自定义', category: '内容模块', allowItems: false, shape: 'text' },
];

export function sectionTitle(type: string): string {
  return sectionRegistry.find((s) => s.type === type)?.title ?? type;
}

/** Ordered categories; the free-form section is always the last root option. */
export const sectionPickerOptions = [
  { value: 'basic', label: '基础资料', children: ['EDUCATION', 'SKILLS', 'GOAL'] },
  {
    value: 'experience',
    label: '经历与项目',
    children: ['WORK_EXPERIENCE', 'INTERNSHIPS', 'PROJECTS', 'CAMPUS', 'VOLUNTEERING'],
  },
  {
    value: 'achievements',
    label: '成果与资质',
    children: ['ACHIEVEMENTS', 'AWARDS', 'CERTIFICATES', 'PUBLICATIONS'],
  },
  {
    value: 'personal',
    label: '个人展示',
    children: ['STRENGTHS', 'HOBBIES', 'SOCIAL_LINKS', 'REFERENCES', 'CHARTS'],
  },
].map((group) => ({
  ...group,
  children: group.children.map((type) => ({ value: type, label: sectionTitle(type) })),
}));
export const modulePickerOptions = [...sectionPickerOptions, { value: 'TEXT', label: '自定义' }];
