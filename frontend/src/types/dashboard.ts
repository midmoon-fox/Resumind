import type { ResumeTemplateId } from './templates';

export interface ResumeSummary {
  id: string;
  title: string;
  role: string;
  template: ResumeTemplateId;
  status: 'draft' | 'ready';
  updatedAt: string;
  completeness: number;
}

export type FeatureKey = 'generator' | 'jobs' | 'interview';

export interface FeatureInfo {
  title: string;
  description: string;
  steps: string[];
}
