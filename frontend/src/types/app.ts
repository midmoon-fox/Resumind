import type { ResumeSummary } from './dashboard';
import type { ResumeTemplateId } from './templates';
import type { Schema } from '../services/schema';

export interface Profile {
  photoData?: string | null;
  educationFirstId?: string;
  skillItems?: string[];
  education?: Schema<'resume_b__schemas__Education'>[];
  age?: number | null;
  name: string;
  email: string;
  phone: string;
  city: string;
  school: string;
  major: string;
  degree: string;
  educationPeriod: string;
  skills: string;
  summary: string;
}
export interface ResumeItem {
  id: string;
  title: string;
  subtitle: string;
  period: string;
  html: string;
}
export interface ChartDatum {
  label: string;
  value: number;
  unit: string;
}
export interface SocialLink {
  platform: string;
  label: string;
  url: string;
}
export interface ResumeSection {
  id: string;
  title: string;
  kind: string;
  hidden: boolean;
  items: ResumeItem[];
  chartData?: ChartDatum[];
  links?: SocialLink[];
  text?: string;
}
export interface ResumeStyle {
  accent: string;
  font: string;
  fontSize: number;
  lineHeight: number;
  sectionGap: number;
}
export interface ResumeDocument extends ResumeSummary {
  versionId?: string;
  backend?: Schema<'ResumeOutput'>;
  profile: Profile;
  sections: ResumeSection[];
  style: ResumeStyle;
  revision: number;
  jdSnapshot?: JobDescription;
}
export interface ResumeVersion {
  id: string;
  resumeId: string;
  label: string;
  createdAt: string;
  document: ResumeDocument;
}
export interface JobDescription {
  backend?: Schema<'JdOut'>;
  version?: Schema<'JdVersionOut'>;
  id: string;
  title: string;
  company: string;
  city: string;
  text: string;
  tags: string[];
  createdAt: string;
  source: 'manual' | 'demo' | 'recommendation';
}
export interface Experience {
  backend?: Schema<'ExperienceOut'>;
  id: string;
  type: string;
  title: string;
  role: string;
  period: string;
  description: string;
  confirmed: boolean;
  excluded: boolean;
}
export interface Workspace {
  backend?: Schema<'WorkspaceOut'>;
  title: string;
  direction: string;
  step: number;
  jdId: string;
  profile: Profile;
  materialsText: string;
  answerDraft: string;
  files: { name: string; size: number; materialId?: string; id?: string }[];
  experiences: Experience[];
  answers: string[];
  questionIndex: number;
  template: ResumeTemplateId;
}
export interface InterviewQuestion {
  id: string;
  question: string;
  answer: string;
  personalAnswer: string;
}
export interface Preparation {
  backend?: Schema<'PreparationOutput'>;
  id: string;
  resumeId: string;
  revision: number;
  title: string;
  profileName: string;
  createdAt: string;
  intro: string;
  questions: InterviewQuestion[];
}
export interface AppState {
  resumes: ResumeDocument[];
  versions: ResumeVersion[];
  jds: JobDescription[];
  preparations: Preparation[];
  workspace: Workspace;
  account: { nickname: string; initials: string; avatar: string; city: string; direction: string };
  notifications: { saveReminder: boolean; interviewReminder: boolean };
  favorites: string[];
  demoSignedIn: boolean;
  goals: boolean[];
}
