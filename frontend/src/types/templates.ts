export type ResumeTemplateId = 'simple' | 'project' | 'ribbon' | 'sidebar' | 'modern' | 'campus' | 'academic' | 'creative';

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
    id: 'ribbon',
    title: '紫韵雅致',
    category: '通用简历',
    desc: '淡紫飘带标题与细线分区，整洁而有层次。',
    suitableFor: '法务、行政及专业服务岗位',
  },
  {
    id: 'sidebar',
    title: '蓝灰双栏',
    category: '校园求职',
    desc: '照片与联系信息独立侧栏，经历在右侧清晰展开。',
    suitableFor: '校园招聘及运营服务岗位',
  },
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
