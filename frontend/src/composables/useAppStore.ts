import { reactive, ref } from 'vue';
import type { AppState, Profile, ResumeDocument, ResumeSection, Workspace } from '../types/app';
import { sectionRegistry } from '../types/sectionRegistry';
import type { Schema } from '../services/schema';
import {
  api,
  allPages,
  ApiError,
  clearSessionToken,
  localFileUrl,
  authenticatedFetch,
  setAccessToken,
  restoreAccessToken,
} from '../services/client';
import {
  fromResume,
  resumeCompletion,
  fromProfile,
  fromJd,
  fromExperience,
  toDocument,
  toStyle,
  toProfile,
  experienceData,
  experienceType,
} from '../services/mapping';
import { clearTasks } from '../services/tasks';

export const emptyProfile = (): Profile => ({
  name: '',
  email: '',
  phone: '',
  city: '',
  school: '',
  major: '',
  degree: '本科',
  educationPeriod: '',
  skills: '',
  summary: '',
});
export const emptyWorkspace = (): Workspace => ({
  title: '',
  direction: '',
  step: 0,
  jdId: '',
  profile: emptyProfile(),
  materialsText: '',
  answerDraft: '',
  files: [],
  experiences: [],
  answers: [],
  questionIndex: 0,
  template: 'simple',
});
export const defaultStyle = () => ({
  accent: '#333333',
  font: 'Microsoft YaHei',
  fontSize: 11,
  lineHeight: 1.65,
  sectionGap: 18,
});
export function makeSection(kind: string): ResumeSection {
  const def = sectionRegistry.find((s) => s.type === kind);
  const isChart = def?.shape === 'chart';
  const isLinks = def?.shape === 'links';
  const isText = def?.shape === 'text';
  const isProfile = !!def && !def.allowItems && !isChart && !isLinks && !isText;
  return {
    id: crypto.randomUUID(),
    title: def?.title ?? kind,
    kind,
    hidden: false,
    items: !isProfile && !isChart && !isLinks && !isText ? [{ id: crypto.randomUUID(), title: '', subtitle: '', period: '', html: '<p></p>' }] : [],
    chartData: isChart ? [{ label: '', value: 0, unit: '' }] : undefined,
    links: isLinks ? [{ platform: '', label: '', url: '' }] : undefined,
    text: isText ? '<p></p>' : undefined,
  };
}
export function exampleProfile(): Profile {
  return {
    ...emptyProfile(),
    name: '林同学',
    email: 'lin@example.com',
    phone: '13800000000',
    school: '示例大学',
    major: '计算机科学与技术',
    degree: '本科',
    educationPeriod: '2023-09 – 2027-06',
    skills: 'Vue\nTypeScript\nJavaScript\nHTML\nCSS\nGit',
  };
}
function seed(): AppState {
  return {
    resumes: [],
    versions: [],
    preparations: [],
    jds: [],
    workspace: emptyWorkspace(),
    account: { nickname: '', initials: '', avatar: '', city: '', direction: '' },
    notifications: { saveReminder: true, interviewReminder: true },
    favorites: [],
    demoSignedIn: false,
    goals: [false, false, false],
  };
}
const state = reactive<AppState>(seed());
const user = ref<Schema<'UserOut'> | null>(null);
const templates = ref<Schema<'TemplateOutput'>[]>([]);
const lastSaveError = ref('');
const storageStatus = ref<'saved' | 'pending' | 'error'>('saved');
const authWarning = ref('');
const loading = ref(false),
  loadError = ref('');
let initialization: Promise<void> | undefined;
let avatarUrl = '';
const saveQueues = new Map<string, Promise<void>>();
const saveTimers = new Map<string, ReturnType<typeof setTimeout>>();
const preferenceKey = () => `resume-star-preferences:${user.value?.id}`;
function persist() {
  if (!user.value) return;
  localStorage.setItem(
    preferenceKey(),
    JSON.stringify({
      favorites: state.favorites,
      notifications: state.notifications,
      goals: state.goals,
      city: state.account.city,
      direction: state.account.direction,
    }),
  );
}
async function setUser(next: Schema<'UserOut'>) {
  user.value = next;
  state.demoSignedIn = true;
  state.account.nickname = next.username;
  state.account.initials = next.username.slice(-1);
  if (avatarUrl) URL.revokeObjectURL(avatarUrl);
  state.account.avatar = '';
  avatarUrl = '';
  if (next.avatarFileId) {
    const data = await api<Schema<'DownloadOut'>>(`/api/files/${next.avatarFileId}/download`);
    const response = await authenticatedFetch(localFileUrl(data.url));
    if (response.ok) {
      avatarUrl = URL.createObjectURL(await response.blob());
      state.account.avatar = avatarUrl;
    }
  }
}
function discardWorkspace() {
  state.workspace = emptyWorkspace();
  persist();
}
async function refreshAccount() {
  await setUser(await api<Schema<'UserOut'>>('/api/me'));
}
async function refreshResume(id: string) {
  const value = fromResume(await api<Schema<'ResumeOutput'>>(`/api/resumes/${id}`));
  const index = state.resumes.findIndex((r) => r.id === id);
  if (index < 0) state.resumes.unshift(value);
  else Object.assign(state.resumes[index]!, value);
  return state.resumes.find((r) => r.id === id)!;
}
async function loadVersions(id: string) {
  const rows = await allPages<Schema<'VersionOutput'>>(`/api/resumes/${id}/versions`);
  const parent = state.resumes.find((r) => r.id === id)?.backend;
  if (!parent) return;
  state.versions = [
    ...state.versions.filter((v) => v.resumeId !== id),
    ...rows.map((v) => ({
      id: v.id,
      resumeId: id,
      label: v.label,
      createdAt: v.createdAt,
      document: {
        ...fromResume({
          ...parent,
          ...v,
          id,
          title: parent.title,
          revision: v.sourceRevision,
          updatedAt: v.createdAt,
        }),
        versionId: v.id,
      },
    })),
  ];
}
async function refreshWorkspace(id: string) {
  const w = await api<Schema<'WorkspaceOut'>>(`/api/workspaces/${id}`);
  const [experiences, materials] = await Promise.all([
    allPages<Schema<'ExperienceOut'>>(`/api/experiences?workspaceId=${id}`),
    allPages<Schema<'MaterialOut'>>(`/api/materials?workspaceId=${id}`),
  ]);
  Object.assign(state.workspace, {
    backend: w,
    title: w.title,
    direction: w.direction ?? '',
    profile: fromProfile(w.profile),
    jdId: state.jds.find((j) => j.version?.id === w.jdVersionId)?.id ?? '',
    step: { JD: 0, PROFILE: 1, MATERIALS: 2, FOLLOWUP: 3, EDITOR: 4 }[w.step],
    experiences: experiences.map(fromExperience),
    files: materials.map((m) => ({
      materialId: m.id,
      id: m.fileId ?? undefined,
      name: m.title,
      size: 0,
    })),
  });
  persist();
}
async function refreshData() {
  loading.value = true;
  loadError.value = '';
  try {
    const [resumes, jds, ts] = await Promise.all([
      allPages<Schema<'ResumeOutput'>>('/api/resumes'),
      allPages<Schema<'JdOut'>>('/api/job-descriptions'),
      allPages<Schema<'TemplateOutput'>>('/api/templates'),
    ]);
    state.resumes = resumes.map(fromResume);
    templates.value = ts;
    state.jds = await Promise.all(
      jds.map(async (j) =>
        fromJd(
          j,
          await api<Schema<'JdVersionOut'>>(
            `/api/job-descriptions/${j.id}/versions/${j.currentVersionId}`,
          ),
        ),
      ),
    );
    await Promise.all(resumes.map((r) => loadVersions(r.id)));
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '数据加载失败';
    throw e;
  } finally {
    loading.value = false;
  }
}
async function initialize() {
  if (!initialization)
    initialization = (async () => {
      try {
        if (!restoreAccessToken()) return;
        await setUser(await api<Schema<'UserOut'>>('/api/me'));
        let prefs: Record<string, any> = {};
        try {
          prefs = JSON.parse(localStorage.getItem(preferenceKey()) ?? '{}');
        } catch {
          /* invalid local preferences */
        }
        state.favorites = prefs.favorites ?? [];
        state.notifications = prefs.notifications ?? state.notifications;
        state.goals = prefs.goals ?? state.goals;
        state.account.city = prefs.city ?? '';
        state.account.direction = prefs.direction ?? '';
        await refreshData();
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          clearSessionToken();
          user.value = null;
          state.demoSignedIn = false;
        } else {
          loadError.value = e instanceof Error ? e.message : '连接失败';
        }
      }
    })();
  await initialization;
}
async function login(email: string, password: string, username?: string) {
  if (username !== undefined)
    await api<Schema<'UserOut'>>('/api/auth/registrations', 'POST', { email, password, username });
  const result = await api<Schema<'LoginOut'>>('/api/auth/sessions', 'POST', { email, password });
  if (
    result.tokenType !== 'Bearer' ||
    typeof result.accessToken !== 'string' ||
    !result.accessToken ||
    result.accessToken.length > 4096
  )
    throw new Error('登录响应不符合 JWT 接口约定');
  authWarning.value = setAccessToken(result.accessToken, result.expiresAt)
    ? ''
    : '浏览器不允许保存登录状态，本次登录仅在当前页面有效。';
  clearTasks();
  Object.assign(state, seed());
  initialization = undefined;
  await initialize();
  if (!user.value) throw new Error(loadError.value || '登录状态验证失败，请重试');
}
async function logout() {
  await flushAll();
  await api('/api/auth/session', 'DELETE');
  clearSessionToken();
  clearTasks();
  user.value = null;
  Object.assign(state, seed());
  initialization = undefined;
  loadError.value = '';
  authWarning.value = '';
}
window.addEventListener('session-expired', () => {
  clearSessionToken();
  clearTasks();
  user.value = null;
  Object.assign(state, seed());
  initialization = undefined;
  window.location.assign('/login');
});
function touchResume(doc: ResumeDocument) {
  Object.assign(doc, resumeCompletion(doc));
  storageStatus.value = 'pending';
  const timer = saveTimers.get(doc.id);
  if (timer) clearTimeout(timer);
  saveTimers.set(
    doc.id,
    setTimeout(() => {
      saveTimers.delete(doc.id);
      void saveResume(doc).catch(() => {});
    }, 900),
  );
}
function canonical(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object')
    return (
      '{' +
      Object.entries(value)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([k, v]) => JSON.stringify(k) + ':' + canonical(v))
        .join(',') +
      '}'
    );
  return JSON.stringify(value);
}
async function saveResume(doc: ResumeDocument) {
  const pending = saveQueues.get(doc.id);
  if (pending) {
    await pending;
    return saveResume(doc);
  }
  const timer = saveTimers.get(doc.id);
  if (timer) clearTimeout(timer);
  saveTimers.delete(doc.id);
  let payload: Schema<'PatchResume'>;
  try {
    payload = {
      baseRevision: doc.revision,
      title: doc.title,
      document: toDocument(doc),
      style: toStyle(doc),
      templateId: doc.template,
      templateVersion:
        templates.value.find((t) => t.id === doc.template)?.version ??
        doc.backend?.templateVersion ??
        '1.0.0',
    };
  } catch (e) {
    storageStatus.value = 'error';
    lastSaveError.value = e instanceof Error ? e.message : '保存失败';
    throw e;
  }
  if (
    doc.backend &&
    canonical([
      payload.title,
      payload.document,
      payload.style,
      payload.templateId,
      payload.templateVersion,
    ]) ===
      canonical([
        doc.backend.title,
        doc.backend.document,
        doc.backend.style,
        doc.backend.templateId,
        doc.backend.templateVersion,
      ])
  ) {
    storageStatus.value = 'saved';
    lastSaveError.value = '';
    return;
  }
  const before = canonical({
    title: doc.title,
    document: payload.document,
    style: payload.style,
    template: doc.template,
  });
  const job = (async () => {
    try {
      const saved = await api<Schema<'ResumeOutput'>>(`/api/resumes/${doc.id}`, 'PATCH', payload);
      doc.backend = saved;
      doc.revision = saved.revision;
      doc.updatedAt = saved.updatedAt;
      const after = canonical({
        title: doc.title,
        document: toDocument(doc),
        style: toStyle(doc),
        template: doc.template,
      });
      storageStatus.value = before === after ? 'saved' : 'pending';
      lastSaveError.value = '';
    } catch (e) {
      storageStatus.value = 'error';
      lastSaveError.value = e instanceof Error ? e.message : '保存失败';
      throw e;
    }
  })();
  saveQueues.set(doc.id, job);
  try {
    await job;
  } finally {
    saveQueues.delete(doc.id);
  }
}
async function flushAll() {
  for (const doc of state.resumes)
    if (saveTimers.has(doc.id) || saveQueues.has(doc.id) || lastSaveError.value)
      await saveResume(doc);
}
async function createResume(title: string, role: string, profile = emptyProfile()) {
  const section = (type: 'EDUCATION' | 'SKILLS', title: string) => ({
    id: crypto.randomUUID(),
    type,
    title,
    visible: true,
    items: [],
  });
  const r = await api<Schema<'ResumeOutput'>>('/api/resumes', 'POST', {
    title: title || '未命名简历',
    document: {
      schemaVersion: '1.0.0',
      profile: toProfile(profile, role),
      sections: [section('EDUCATION', '教育背景'), section('SKILLS', '专业技能')],
    },
    templateId: 'simple',
    templateVersion: '1.1.0',
    style: {
      fontFamily: 'Microsoft YaHei',
      fontSize: 11,
      lineHeight: 1.65,
      accentColor: '#333333',
      sectionGap: 18,
    },
  });
  state.resumes.unshift(fromResume(r));
  return state.resumes[0]!;
}
async function snapshot(doc: ResumeDocument, label = '手动保存') {
  await saveResume(doc);
  const version = await api<Schema<'VersionOutput'>>(`/api/resumes/${doc.id}/versions`, 'POST', {
    baseRevision: doc.revision,
    label,
  });
  await loadVersions(doc.id);
  return state.versions.find((v) => v.id === version.id)!;
}
async function copyResume(doc: ResumeDocument) {
  const result = await api<Schema<'ResumeOutput'>>(`/api/resumes/${doc.id}/copies`, 'POST', {
    title: doc.title + ' · 副本',
  });
  state.resumes.unshift(fromResume(result));
  return state.resumes[0]!;
}
async function deleteResume(id: string) {
  await api(`/api/resumes/${id}`, 'DELETE');
  const timer = saveTimers.get(id);
  if (timer) clearTimeout(timer);
  saveTimers.delete(id);
  state.resumes = state.resumes.filter((r) => r.id !== id);
  state.versions = state.versions.filter((v) => v.resumeId !== id);
  state.preparations = state.preparations.filter((p) => p.resumeId !== id);
}
async function restoreVersion(id: string) {
  const version = state.versions.find((v) => v.id === id)!;
  const doc = state.resumes.find((r) => r.id === version.resumeId)!;
  await saveResume(doc);
  await api(`/api/resumes/${doc.id}/restorations`, 'POST', {
    baseRevision: doc.revision,
    versionId: id,
  });
  await refreshResume(doc.id);
  await loadVersions(doc.id);
}
async function saveWorkspace(step?: Schema<'WorkspacePatch'>['step']) {
  const d = state.workspace;
  if (!d.backend)
    d.backend = await api<Schema<'WorkspaceOut'>>('/api/workspaces', 'POST', {
      title: d.title || '我的简历工作区',
      ...(d.direction.trim() ? {direction: d.direction.trim()} : {}),
    });
  const jd = state.jds.find((j) => j.id === d.jdId);
  d.backend = await api<Schema<'WorkspaceOut'>>(`/api/workspaces/${d.backend.id}`, 'PATCH', {
    baseRevision: d.backend.revision,
    title: d.title || '我的简历工作区',
    direction: d.direction || null,
    profile: toProfile(d.profile, d.direction),
    jdVersionId: jd?.version?.id ?? null,
    ...(step ? { step } : {}),
  });
  persist();
  return d.backend;
}
async function saveExperiences() {
  await saveWorkspace();
  for (const e of state.workspace.experiences) {
    const data = experienceData(e);
    if (!e.backend) {
      e.backend = await api<Schema<'ExperienceOut'>>('/api/experiences', 'POST', {
        workspaceId: state.workspace.backend!.id,
        type: experienceType(e.type),
        data,
      });
      e.id = e.backend.id;
    }
    e.backend = await api<Schema<'ExperienceOut'>>(`/api/experiences/${e.id}`, 'PATCH', {
      baseRevision: e.backend.revision,
      type: experienceType(e.type),
      data,
      status: e.confirmed ? 'CONFIRMED' : 'CANDIDATE',
      excluded: e.excluded,
    });
  }
}
export function useAppStore() {
  return {
    state,
    user,
    templates,
    storageStatus,
    lastSaveError,
    loading,
    loadError,
    initialize,
    login,
    logout,
    authWarning,
    persist,
    refreshAccount,
    refreshData,
    refreshResume,
    loadVersions,
    refreshWorkspace,
    saveResume,
    flushAll,
    discardWorkspace,
    saveWorkspace,
    saveExperiences,
    createResume,
    touchResume,
    snapshot,
    copyResume,
    deleteResume,
    restoreVersion,
  };
}
