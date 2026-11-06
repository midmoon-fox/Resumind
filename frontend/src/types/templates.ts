export type ResumeTemplateId = 'simple' | 'project' | 'modern' | 'campus' | 'academic' | 'creative';

export type ResumeTemplateCategory = '通用简历' | '校园求职' | '创意设计';

export interface ResumeTemplateOption {
  id: ResumeTemplateId;
  title: string;
  category: ResumeTemplateCategory;
  desc: string;
  suitableFor: string;
}

export const resumeTemplates: ResumeTemplateOption[] = [
  {
    id: 'simple',
    title: '简洁通用',
    category: '通用简历',
    desc: '清爽单栏，重点清晰，阅读顺畅。',
    suitableFor: '大多数岗位',
  },
  {
    id: 'project',
    title: '项目突出',
    category: '通用简历',
    desc: '醒目抬头与分区标题，突出项目经历。',
    suitableFor: '项目经验较多',
  },
];

export const resumeTemplateCategories = ['全部模板', '通用简历', '校园求职', '创意设计'] as const;
