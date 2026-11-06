import type { ResumeSummary } from '../types/dashboard';

// 本地初始示例，后续由 services 层替换为接口数据。

export const mockResumes: ResumeSummary[] = [
  {
    id: 'demo-frontend',
    title: '前端开发工程师',
    role: '前端开发',
    template: 'simple',
    status: 'draft',
    updatedAt: '2026-11-06T01:30:00+08:00',
    completeness: 80,
  },
  {
    id: 'demo-product',
    title: '产品经理 · 校园招聘',
    role: '产品经理',
    template: 'project',
    status: 'ready',
    updatedAt: '2026-11-05T15:20:00+08:00',
    completeness: 100,
  },
  {
    id: 'demo-design',
    title: 'UI 设计师 · 实习',
    role: 'UI 设计',
    template: 'simple',
    status: 'draft',
    updatedAt: '2026-11-03T10:10:00+08:00',
    completeness: 65,
  },
];
