export interface DemoJob {
  id: string;
  title: string;
  company: string;
  city: string;
  salary: string;
  level: string;
  tags: string[];
  description: string;
}
export const demoJobs: DemoJob[] = [
  {
    id: 'job-fe-1',
    title: '前端开发工程师',
    company: '星河科技（示例）',
    city: '杭州',
    salary: '12–18K · 示例',
    level: '应届生',
    tags: ['Vue', 'TypeScript', 'CSS'],
    description:
      '参与 Web 产品页面开发，维护 Vue 组件，使用 TypeScript 提升代码质量。要求掌握 HTML、CSS 与 JavaScript，了解接口联调及响应式布局。',
  },
  {
    id: 'job-fe-2',
    title: 'Web 前端实习生',
    company: '光合实验室（示例）',
    city: '上海',
    salary: '200–300 元/天 · 示例',
    level: '实习',
    tags: ['JavaScript', 'Vue', 'Git'],
    description:
      '协助完成产品前端页面，优化交互细节，参与组件文档与基础测试。要求熟悉 JavaScript、Vue 和 Git。',
  },
  {
    id: 'job-pm',
    title: '产品经理',
    company: '远山数字（示例）',
    city: '杭州',
    salary: '10–16K · 示例',
    level: '应届生',
    tags: ['需求分析', '原型设计', '数据分析'],
    description:
      '参与用户调研、需求分析、原型设计与项目推进，能够清晰表达产品方案，关注用户体验与数据反馈。',
  },
  {
    id: 'job-ui',
    title: 'UI / UX 设计师',
    company: '拾光设计（示例）',
    city: '北京',
    salary: '10–15K · 示例',
    level: '应届生',
    tags: ['Figma', '交互设计', '视觉设计'],
    description:
      '参与 Web 与移动端界面设计，维护设计规范，使用 Figma 交付组件和交互原型，协同前端完成视觉还原。',
  },
  {
    id: 'job-fe-3',
    title: '前端开发工程师',
    company: '云屿软件（示例）',
    city: '深圳',
    salary: '15–22K · 示例',
    level: '1–3年',
    tags: ['React', 'TypeScript', '工程化'],
    description: '负责业务组件与前端工程化建设，熟悉 React、TypeScript、浏览器基础和性能优化。',
  },
];
