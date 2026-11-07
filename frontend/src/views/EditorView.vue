<script setup lang="ts">
import ProfilePhoto from '../components/resume/ProfilePhoto.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  Download,
  Eye,
  EyeOff,
  Plus,
  Save,
  Trash2,
  Undo2,
  Redo2,
} from '@lucide/vue';
import AdditionalEducation from '../components/resume/AdditionalEducation.vue';
import EducationDates from '../components/resume/EducationDates.vue';
import EditorModuleTitle from '../components/resume/EditorModuleTitle.vue';
import { ElMessageBox } from 'element-plus';
import BaseButton from '../components/common/BaseButton.vue';
import { resumeTemplates } from '../types/templates';
import { themeColors } from '../types/themeColors';
import { latestTemplate, supportsTheme } from '../services/templatePolicy';
import { modulePickerOptions } from '../types/sectionRegistry';
import BaseModal from '../components/common/BaseModal.vue';
import AiResult from '../components/common/AiResult.vue';
import AiTextField from '../components/common/AiTextField.vue';
import ResumeDocumentView from '../components/resume/ResumeDocument.vue';
import { makeSection, useAppStore } from '../composables/useAppStore';
import { useToast } from '../composables/useToast';
import type { EditTarget } from '../services/editorTargets';
import { useAiFieldWriter } from '../composables/useAiFieldWriter';
import { dateText } from '../utils/content';
import { api, download } from '../services/client';
import { waitTask } from '../services/tasks';
import type { Schema } from '../services/schema';
const route = useRoute(),
  router = useRouter();
const crypto = window.crypto;
const {
  state,
  loading,
  storageStatus,
  touchResume,
  snapshot,
  restoreVersion,
  saveResume,
  lastSaveError,
  loadVersions,
  refreshResume,
  templates,
} = useAppStore();
const { success, error } = useToast();
const doc = computed(() => state.resumes.find((r) => r.id === route.params.id));
const availableThemeColors = computed(() => {
  const template = latestTemplate(templates.value, doc.value?.template ?? '');
  return themeColors.filter((color) => supportsTheme(template, color.value));
});
function chooseThemeColor(color: string) {
  const current = doc.value;
  if (!current) return;
  if (!supportsTheme(latestTemplate(templates.value, current.template), color)) {
    error('当前模板不支持这个颜色，请选择其他主题颜色。');
    return;
  }
  current.style.accent = color;
}
const {
  busy: aiBusy,
  notice: aiNotice,
  run: runAi,
  pending: aiPending,
  apply: applyAi,
  activeKey: aiKey,
} = useAiFieldWriter({
  getDoc: () => doc.value,
  saveResume,
  refreshResume,
  onApplied: () => success('已填入，可撤销'),
});
function aiDescribe(section: { id: string }, item: { id: string }) {
  return runAi(
    { kind: 'ITEM_DESCRIPTION', sectionId: section.id, itemId: item.id },
    '根据当前岗位要求与真实经历组织为简洁中文，保留事实，不新增经历或指标',
  );
}
function addChartDatum(section: { chartData?: { label: string; value: number; unit: string }[] }) {
  (section.chartData ?? (section.chartData = [])).push({ label: '', value: 0, unit: '' });
}
function removeChartDatum(
  section: { chartData?: { label: string; value: number; unit: string }[] },
  index: number,
) {
  (section.chartData ?? []).splice(index, 1);
}
function addLink(section: { links?: { platform: string; label: string; url: string }[] }) {
  (section.links ?? (section.links = [])).push({ platform: '', label: '', url: '' });
}
function removeLink(
  section: { links?: { platform: string; label: string; url: string }[] },
  index: number,
) {
  (section.links ?? []).splice(index, 1);
}
function aiProfile(field: 'education' | 'skills') {
  if (!doc.value) return;
  let section = doc.value.sections.find((s) => s.kind === field.toUpperCase());
  if (!section) {
    section = makeSection(field.toUpperCase());
    doc.value.sections.push(section);
  }
  return runAi(
    { kind: 'PROFILE_FIELD', sectionId: section.id, field },
    '根据已有真实资料及岗位要求优化表达，不新增学校、技能或经历',
  );
}
function aiSectionText(section: { id: string }) {
  return runAi(
    { kind: 'SECTION_FIELD', sectionId: section.id, field: 'text' },
    '根据当前岗位要求与真实经历组织为简洁中文，保留事实，不新增经历或指标',
  );
}
const openCards = ref<string[]>([]);
const removedCore = ref<string[]>([]);
async function deleteModule(key: string, title: string) {
  if (key === 'basic') return;
  const current = doc.value;
  if (!current) return;
  try {
    await ElMessageBox.confirm(`确定删除“${title}”及其内容吗？删除后可用顶部撤销恢复。`, '确认删除模块', {
      confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning',
      confirmButtonClass: 'el-button--danger', closeOnClickModal: false,
    });
  } catch { return; }
  if (doc.value?.id !== current.id) return;
  past.value.push(content());
  future.value = [];
  replaying = true;
  try {
  if (key === 'education') {
    Object.assign(current.profile, { school: '', major: '', degree: '', educationPeriod: '', education: [] });
    current.sections = current.sections.filter((s) => s.kind !== 'EDUCATION');
    removedCore.value.push(key);
  } else if (key === 'skills') {
    current.profile.skills = '';
    current.profile.skillItems = [];
    current.sections = current.sections.filter((s) => s.kind !== 'SKILLS');
    removedCore.value.push(key);
  } else {
    current.sections = current.sections.filter((s) => s.id !== key);
  }
  } finally { replaying = false; }
  openCards.value = openCards.value.filter((id) => id !== key);
  success('模块已删除，可点击顶部撤销恢复');
}
const modulePickerValue = ref<string>();
async function pickModule(value: unknown) {
  if (typeof value !== 'string' || !value) return;
  const core = ({ EDUCATION: 'education', SKILLS: 'skills' } as Record<string, string>)[value];
  if (core && removedCore.value.includes(core)) {
    removedCore.value = removedCore.value.filter((key) => key !== core);
    if (!doc.value?.sections.some((s) => s.kind === value)) addSection(value);
    openCards.value = [...openCards.value, core];
    await nextTick();
    modulePickerValue.value = undefined;
    return;
  }
  addSection(value);
  const created = doc.value?.sections.at(-1);
  if (created) openCards.value = [...openCards.value, created.id];
  await nextTick();
  modulePickerValue.value = undefined;
}
function addSection(value: string) {
  if (value && doc.value) {
    doc.value.sections.push(makeSection(value));
  }
}
const tab = ref('content');
const mobileView = ref('edit');
// 编辑页占满视口，左右块各自滚动，屏蔽主滚动条
onMounted(() => {
  document.body.style.overflow = 'hidden';
});
onBeforeUnmount(() => {
  document.body.style.overflow = '';
});
// 点击预览定位到对应编辑卡片
async function focusEditorTarget(target: EditTarget) {
  if (!doc.value) return;
  if (
    !['basic', 'education', 'skills'].includes(target.key) &&
    !doc.value.sections.some((s) => s.id === target.key)
  )
    return;
  if (
    target.itemId &&
    !doc.value.sections.some(
      (s) => s.id === target.key && s.items.some((i) => i.id === target.itemId),
    )
  )
    return;
  tab.value = 'content';
  if (mobileView.value === 'preview') mobileView.value = 'edit';
  if (!openCards.value.includes(target.key)) openCards.value.push(target.key);
  await nextTick();
  setTimeout(() => {
    const anchor = document.getElementById(`edit-card-${target.key}`);
    anchor?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const input = target.itemId
      ? document.querySelector<HTMLElement>(
          `[data-item-id="${target.itemId}"] input, [data-item-id="${target.itemId}"] textarea, [data-item-id="${target.itemId}"] .rich-editor`,
        )
      : target.field === 'name'
        ? document.querySelector<HTMLElement>('[data-field="name"] input')
        : (anchor
            ?.closest('.el-collapse-item')
            ?.querySelector<HTMLElement>('textarea, input, .tiptap, [contenteditable=true]') ??
          null);
    input?.focus();
  }, 350);
}
const exportOpen = ref(false),
  historyOpen = ref(false);
const exportName = ref(''),
  format = ref('pdf'),
  exportBusy = ref(false);
const issues = ref<string[]>([]);
const operationBusy = ref(false);
let syncing = false;
async function attempt(action: () => Promise<void>) {
  if (operationBusy.value) return;
  operationBusy.value = true;
  try {
    await action();
  } catch (e) {
    error(e instanceof Error ? e.message : '操作失败');
  } finally {
    operationBusy.value = false;
  }
}
const versions = computed(() => state.versions.filter((v) => v.resumeId === doc.value?.id));
const selectedVersion = ref('');
const selectedSnapshot = computed(() => versions.value.find((v) => v.id === selectedVersion.value));
const restoreConfirm = ref(false);
const versionLabel = ref('');
const past = ref<string[]>([]),
  future = ref<string[]>([]);
let replaying = false;
const content = () =>
  doc.value
    ? JSON.stringify({
        id: doc.value.id,
        title: doc.value.title,
        role: doc.value.role,
        profile: doc.value.profile,
        sections: doc.value.sections,
        style: doc.value.style,
        template: doc.value.template,
      })
    : '';
watch(
  content,
  (next, previous) => {
    if (!doc.value || !previous || JSON.parse(previous).id !== doc.value.id) {
      past.value = [];
      future.value = [];
      return;
    }
    if (next === previous) return;
    if (!replaying) {
      past.value.push(previous);
      if (past.value.length > 60) past.value.shift();
      future.value = [];
    }
    if (!syncing) touchResume(doc.value);
  },
  { flush: 'sync' },
);
function undo() {
  if (!doc.value || !past.value.length) return;
  future.value.push(content());
  replaying = true;
  Object.assign(doc.value, JSON.parse(past.value.pop()!));
  removedCore.value = [];
  replaying = false;
}
function redo() {
  if (!doc.value || !future.value.length) return;
  past.value.push(content());
  replaying = true;
  Object.assign(doc.value, JSON.parse(future.value.pop()!));
  replaying = false;
}
function move(index: number, direction: number) {
  if (!doc.value) return;
  const target = index + direction;
  if (target < 0 || target >= doc.value.sections.length) return;
  const sections = [...doc.value.sections];
  [sections[index], sections[target]] = [sections[target]!, sections[index]!];
  doc.value.sections = sections;
}
async function saveVersion() {
  await attempt(async () => {
    if (!doc.value) return;
    await snapshot(doc.value, versionLabel.value.trim() || '手动保存');
    versionLabel.value = '';
    success('版本已保存到服务端');
  });
}
async function doRestore() {
  await attempt(async () => {
    syncing = true;
    try {
      await restoreVersion(selectedVersion.value);
    } finally {
      syncing = false;
    }
    historyOpen.value = false;
    restoreConfirm.value = false;
    success('已恢复历史版本');
  });
}
async function retrySave() {
  await attempt(async () => {
    if (doc.value) await saveResume(doc.value);
  });
}
async function doExport() {
  if (!doc.value || exportBusy.value || !exportName.value.trim()) return;
  exportBusy.value = true;
  issues.value = [];
  try {
    await saveResume(doc.value);
    const fileFormat = format.value.toUpperCase() as 'PDF' | 'DOCX' | 'HTML';
    const check = await api<Schema<'PreflightOutput'>>(
      `/api/resumes/${doc.value.id}/preflights`,
      'POST',
      { baseRevision: doc.value.revision, format: fileFormat },
    );
    if (!check.canExport) {
      issues.value = check.issues.map((i) => i.message);
      return;
    }
    const fileName =
      exportName.value.trim().replace(/\.(pdf|docx|html)$/i, '') + '.' + format.value;
    const accepted = await api<Schema<'AsyncAccepted'>>('/api/exports', 'POST', {
      resumeId: doc.value.id,
      baseRevision: doc.value.revision,
      format: fileFormat,
      fileName,
    });
    await waitTask(accepted.taskId);
    await download(`/api/exports/${accepted.resourceId}/download`, fileName);
    await loadVersions(doc.value.id);
    exportOpen.value = false;
    success('后端文件已生成并下载');
  } catch (e) {
    error(e instanceof Error ? e.message : '导出失败');
  } finally {
    exportBusy.value = false;
  }
}
</script>
<template>
  <div v-if="doc" class="editor-page">
    <p v-if="lastSaveError" class="form-error" role="alert">
      {{ lastSaveError }}
      <BaseButton size="small" variant="secondary" @click="retrySave">重试保存</BaseButton>
    </p>
    <header class="editor-heading">
      <div class="editor-title">
        <button class="icon-button" aria-label="返回我的简历" @click="router.push('/resumes')">
          <ArrowLeft :size="20" />
        </button>
        <div>
          <ElInput v-model="doc.title" aria-label="简历名称" maxlength="100" /><small
            :class="{ 'storage-error': storageStatus === 'error' }"
            ><Check :size="12" />{{
              storageStatus === 'pending'
                ? '正在保存到服务端'
                : storageStatus === 'error'
                  ? '保存失败，请查看错误并重试'
                  : '已保存到服务端'
            }}
            / 修订 {{ doc.revision }}</small
          >
        </div>
      </div>
      <div class="editor-actions">
        <button class="icon-button" aria-label="撤销修改" :disabled="!past.length" @click="undo">
          <Undo2 :size="18" /></button
        ><button class="icon-button" aria-label="重做修改" :disabled="!future.length" @click="redo">
          <Redo2 :size="18" />
        </button>
        <BaseButton variant="secondary" size="small" @click="saveVersion"
          ><Save :size="16" />保存</BaseButton
        ><BaseButton
          size="small"
          @click="
            exportName = doc.title;
            exportOpen = true;
          "
          ><Download :size="16" />导出简历</BaseButton
        >
      </div>
    </header>
    <div class="mobile-editor-tabs tabs">
      <button :class="{ active: mobileView === 'edit' }" @click="mobileView = 'edit'">
        编辑内容</button
      ><button :class="{ active: mobileView === 'preview' }" @click="mobileView = 'preview'">
        预览简历
      </button>
    </div>
    <div class="editor-grid">
      <section
        class="editor-controls panel"
        :class="{ 'mobile-editor-hidden': mobileView !== 'edit' }"
      >
        <div class="tabs editor-tabs">
          <button
            v-for="item in [
              { id: 'content', name: '内容' },
              { id: 'design', name: '设计' },
            ]"
            :key="item.id"
            :class="{ active: tab === item.id }"
            @click="tab = item.id"
          >
            {{ item.name }}
          </button>
        </div>
        <template v-if="tab === 'content'"
          ><el-collapse v-model="openCards" class="editor-cards">
            <el-collapse-item name="basic">
              <template #title
                ><EditorModuleTitle title="基本信息" anchor="edit-card-basic" :expanded="openCards.includes('basic')" :removable="false" /></template
              >
              <ProfilePhoto v-model="doc.profile.photoData" />
              <div class="form-grid">
                <label class="field" data-field="name"
                  >姓名<ElInput
                    v-model="doc.profile.name"
                    maxlength="50"
                    aria-label="姓名" /></label
                ><label class="field"
                  >求职方向<ElInput
                    v-model="doc.role"
                    maxlength="100"
                    aria-label="求职方向" /></label
                ><label class="field"
                  >邮箱<ElInput
                    v-model="doc.profile.email"
                    maxlength="100"
                    type="email"
                    aria-label="邮箱" /></label
                ><label class="field"
                  >手机号<ElInput v-model="doc.profile.phone" maxlength="30" aria-label="手机号"
                /></label>
              </div>
            </el-collapse-item>
            <el-collapse-item v-if="!removedCore.includes('education')" name="education">
              <template #title
                ><EditorModuleTitle title="教育经历" anchor="edit-card-education" :expanded="openCards.includes('education')" @remove="deleteModule('education', '教育经历')" /></template
              >
              <div class="form-grid">
                <label class="field"
                  >学校<ElInput
                    v-model="doc.profile.school"
                    maxlength="100"
                    aria-label="学校" /></label
                ><label class="field"
                  >专业<ElInput
                    v-model="doc.profile.major"
                    maxlength="100"
                    aria-label="专业" /></label
                ><label class="field"
                  >学历<ElSelect v-model="doc.profile.degree" aria-label="学历"
                    ><ElOption :value="'本科'" :label="'本科'" />
                    <ElOption :value="'硕士'" :label="'硕士'" />
                    <ElOption :value="'博士'" :label="'博士'" />
                    <ElOption :value="'大专'" :label="'大专'" />
                    <ElOption :value="'其他'" :label="'其他'" /></ElSelect
                ></label>
              </div>
              <label class="field"
                >教育时间<EducationDates
                  v-model="doc.profile.educationPeriod"
                  /></label
              ><AdditionalEducation :profile="doc.profile" />
            </el-collapse-item>
            <el-collapse-item v-if="!removedCore.includes('skills')" name="skills">
              <template #title
                ><EditorModuleTitle title="专业技能" anchor="edit-card-skills" :expanded="openCards.includes('skills')" @remove="deleteModule('skills', '专业技能')" /></template
              >
              <label class="field"
                >专业技能<ElInput
                  v-model="doc.profile.skills"
                  :rows="5"
                  placeholder="自由描述你掌握的技术、工具和能力，无需分点或逐行填写。"
                  maxlength="2000"
                  type="textarea"
                  aria-label="专业技能"
              /></label>
              <ElButton size="small" :loading="aiBusy" @click="aiProfile('skills')"
                >AI 帮助</ElButton
              >
              <p v-if="aiKey === 'skills' && aiNotice" role="status">{{ aiNotice }}</p>
              <AiResult
                :suggestion="aiPending?.key === 'skills' ? aiPending : null"
                :busy="aiBusy"
                @apply="applyAi"
              />
            </el-collapse-item>
            <el-collapse-item
              v-for="(section, index) in doc.sections"
              :key="section.id"
              :name="section.id"
            >
              <template #title
                ><EditorModuleTitle :title="section.title || '未命名模块'" :anchor="`edit-card-${section.id}`" :expanded="openCards.includes(section.id)" @remove="deleteModule(section.id, section.title || '未命名模块')" /></template
              >
              <div class="editor-section-heading">
                <ElInput v-model="section.title" aria-label="模块名称" maxlength="50" /><button
                  class="icon-button"
                  :aria-label="'上移' + section.title"
                  :disabled="index === 0"
                  @click="move(index, -1)"
                >
                  <ArrowUp :size="15" /></button
                ><button
                  class="icon-button"
                  :aria-label="'下移' + section.title"
                  :disabled="index === doc.sections.length - 1"
                  @click="move(index, 1)"
                >
                  <ArrowDown :size="15" /></button
                ><button
                  class="icon-button"
                  :aria-label="(section.hidden ? '显示' : '隐藏') + section.title"
                  @click="section.hidden = !section.hidden"
                >
                  <EyeOff v-if="section.hidden" :size="15" /><Eye v-else :size="15" /></button
                ><button
                  class="icon-button danger-icon"
                  :aria-label="'删除模块' + section.title"
                  @click="deleteModule(section.id, section.title || '未命名模块')"
                >
                  <Trash2 :size="15" />
                </button>
              </div>
              <p v-if="section.hidden" class="field-hint">
                此模块已隐藏，内容保留，不会出现在预览和导出中。
              </p>
              <div v-if="section.kind === 'CHARTS'" class="editor-chart">
                <div
                  v-for="(datum, dIndex) in section.chartData || []"
                  :key="dIndex"
                  class="editor-chart-row"
                >
                  <label class="field"
                    >标签<ElInput
                      v-model="datum.label"
                      maxlength="80"
                      aria-label="图表标签" /></label
                  ><label class="field"
                    >数值(0-100)<ElInputNumber
                      v-model="datum.value"
                      :min="0"
                      :max="100"
                      aria-label="图表数值" /></label
                  ><label class="field"
                    >单位<ElInput
                      v-model="datum.unit"
                      maxlength="20"
                      aria-label="图表单位" /></label
                  ><ElButton
                    type="danger"
                    text
                    size="small"
                    @click="removeChartDatum(section, dIndex)"
                    >删除</ElButton
                  >
                </div>
                <ElButton type="primary" class="editor-card-add" @click="addChartDatum(section)"
                  ><Plus :size="15" />新增数据点</ElButton
                >
              </div>
              <div v-else-if="section.kind === 'SOCIAL_LINKS'" class="editor-links">
                <div
                  v-for="(link, lIndex) in section.links || []"
                  :key="lIndex"
                  class="editor-link-row"
                >
                  <label class="field"
                    >平台<ElInput v-model="link.platform" maxlength="40" aria-label="平台" /></label
                  ><label class="field"
                    >显示名称<ElInput
                      v-model="link.label"
                      maxlength="80"
                      aria-label="显示名称" /></label
                  ><label class="field"
                    >链接<ElInput v-model="link.url" maxlength="500" aria-label="链接" /></label
                  ><ElButton type="danger" text size="small" @click="removeLink(section, lIndex)"
                    >删除</ElButton
                  >
                </div>
                <ElButton type="primary" class="editor-card-add" @click="addLink(section)"
                  ><Plus :size="15" />新增链接</ElButton
                >
              </div>
              <div v-else-if="section.kind === 'TEXT'" class="editor-text">
                <AiTextField
                  :model-value="section.text ?? '<p></p>'"
                  label="文本内容"
                  :busy="aiBusy"
                  :notice="aiKey === section.id + ':text' ? aiNotice : ''"
                  :suggestion="aiPending?.key === section.id + ':text' ? aiPending : null"
                  @apply="applyAi"
                  @update:model-value="section.text = $event"
                  @ai-help="aiSectionText(section)"
                />
              </div>
              <template v-else>
                <div
                  v-for="(item, itemIndex) in section.items"
                  :key="item.id"
                  class="editor-item"
                  :data-item-id="item.id"
                >
                  <div class="form-grid">
                    <label class="field"
                      >经历名称<ElInput
                        v-model="item.title"
                        maxlength="100"
                        aria-label="经历名称" /></label
                    ><label class="field"
                      >角色 / 职位<ElInput
                        v-model="item.subtitle"
                        maxlength="100"
                        aria-label="角色 / 职位"
                    /></label>
                  </div>
                  <label class="field"
                    >时间<ElInput v-model="item.period" maxlength="60" aria-label="时间" /></label
                  ><label class="field">描述</label
                  ><AiTextField
                    :model-value="item.html"
                    :label="'经历描述' + (itemIndex + 1)"
                    :busy="aiBusy"
                    :notice="aiKey === section.id + ':' + item.id ? aiNotice : ''"
                    :suggestion="aiPending?.key === section.id + ':' + item.id ? aiPending : null"
                    @apply="applyAi"
                    @update:model-value="item.html = $event"
                    @ai-help="aiDescribe(section, item)"
                  />
                  <div class="inline-actions">
                    <ElButton
                      type="danger"
                      text
                      size="small"
                      @click="section.items.splice(itemIndex, 1)"
                      >删除条目</ElButton
                    >
                  </div>
                </div>
                <ElButton
                  type="primary"
                  class="editor-card-add"
                  @click="
                    section.items.push({
                      id: crypto.randomUUID(),
                      title: '',
                      subtitle: '',
                      period: '',
                      html: '<p></p>',
                    })
                  "
                  ><Plus :size="15" />新增条目</ElButton
                >
              </template>
            </el-collapse-item>
          </el-collapse>
          <div class="module-picker-row"><ElCascader
            v-model="modulePickerValue"
            class="module-picker"
            :options="modulePickerOptions"
            :props="{ emitPath: false, expandTrigger: 'click' }"
            filterable
            clearable
            :show-all-levels="false"
            placeholder="＋ 新增模块（可搜索）"
            aria-label="新增模块"
            popper-class="module-picker-popper"
            @change="pickModule"
        /></div></template>
        <template v-if="tab === 'design'"
          ><h2 class="editor-block-title wrap-heading">样式设计</h2>
          <label class="field"
            >简历模板<ElSelect v-model="doc.template" aria-label="简历模板"
              ><ElOption
                v-for="template in resumeTemplates"
                :key="template.id"
                :value="template.id"
                :label="
                  String(template.title) + ' ' + '·' + ' ' + String(template.category)
                " /></ElSelect></label
          ><label class="field"
            >主题颜色
            <div class="color-options">
              <button
                v-for="color in availableThemeColors"
                :key="color.value"
                type="button"
                :style="{ background: color.value, color: color.ink }"
                :aria-label="'主题颜色' + color.label"
                :title="color.label"

                :aria-pressed="doc.style.accent.toUpperCase() === color.value"
                @click="chooseThemeColor(color.value)"
              >
                <Check v-if="doc.style.accent.toUpperCase() === color.value" :size="16" />
              </button></div></label
          ><label class="field"
            >字体<ElSelect v-model="doc.style.font" aria-label="字体"
              ><ElOption value="Microsoft YaHei" :label="'微软雅黑'" />
              <ElOption value="SimSun" :label="'宋体'" /></ElSelect></label
          ><label class="field"
            >字号 {{ doc.style.fontSize }} pt<ElSlider
              v-model="doc.style.fontSize"
              :min="10"
              :max="20"
              :step="1"
              aria-label="字号 pt" /></label
          ><label class="field"
            >行高 {{ doc.style.lineHeight
            }}<ElSlider
              v-model="doc.style.lineHeight"
              :min="1.1"
              :max="2"
              :step="0.05"
              aria-label="行高" /></label
          ><label class="field"
            >模块间距 {{ doc.style.sectionGap }} px<ElSlider
              v-model="doc.style.sectionGap"
              :min="0"
              :max="32"
              :step="2"
              aria-label="模块间距 px"
          /></label>
        </template>
      </section>
      <section
        class="editor-preview"
        :class="{ 'mobile-editor-hidden': mobileView !== 'preview' }"
        aria-label="简历实时预览"
      >
        <ResumeDocumentView :document="doc" editable @select-target="focusEditorTarget" />
      </section>
    </div>
    <BaseModal :open="exportOpen" title="让下一份机会，看见你" @close="exportOpen = false"
      ><p class="body-copy">导出当前内容的固定副本，编辑中的后续修改不会混入文件。</p>
      <label class="field"
        >文件名称<ElInput v-model="exportName" maxlength="100" aria-label="文件名称" /></label
      ><label class="field"
        >导出格式<ElSelect v-model="format" aria-label="导出格式"
          ><ElOption value="pdf" :label="'PDF / 后端生成文件'" />
          <ElOption value="docx" :label="'Word / 可编辑 .docx'" />
          <ElOption value="html" :label="'HTML / 独立网页文件'" /></ElSelect
      ></label>
      <div v-if="issues.length" class="error-box" role="alert">
        <strong>请先补全以下信息</strong>
        <ul>
          <li v-for="issue in issues" :key="issue">{{ issue }}</li>
        </ul>
        <BaseButton
          size="small"
          variant="secondary"
          @click="
            exportOpen = false;
            tab = 'content';
            mobileView = 'edit';
          "
          >返回修改</BaseButton
        >
      </div>
      <div v-else class="callout">
        <strong>基础信息检查通过</strong>
        <p>点击开始导出后将由后端执行预检并生成文件。请确保所有经历真实。</p>
      </div>
      <div class="modal-actions">
        <BaseButton variant="secondary" @click="exportOpen = false">取消</BaseButton
        ><BaseButton
          :loading="exportBusy"
          :disabled="!exportName.trim() || exportBusy"
          @click="doExport"
          ><Download :size="16" />{{ exportBusy ? '正在生成…' : '开始导出' }}</BaseButton
        >
      </div></BaseModal
    >
    <BaseModal
      :open="historyOpen"
      title="留住每一次重要修改"
      wide
      @close="
        historyOpen = false;
        restoreConfirm = false;
      "
      ><div class="inline-actions">
        <ElInput
          v-model="versionLabel"
          class="plain-input"
          aria-label="版本备注"
          maxlength="100"
          placeholder="为这次版本写一句备注"
        /><BaseButton size="small" @click="saveVersion">保存当前版本</BaseButton>
      </div>
      <p v-if="!versions.length" class="body-copy">暂时没有历史版本。</p>
      <div v-for="version in versions" :key="version.id" class="history-row">
        <div>
          <strong>{{ version.label }}</strong
          ><small>{{ dateText(version.createdAt) }} / 修订 {{ version.document.revision }}</small>
        </div>
        <BaseButton
          size="small"
          variant="secondary"
          @click="
            selectedVersion = version.id;
            restoreConfirm = false;
          "
          >预览</BaseButton
        >
      </div>
      <template v-if="selectedSnapshot"
        ><div class="document-modal-preview">
          <ResumeDocumentView :document="selectedSnapshot.document" />
        </div>
        <p v-if="restoreConfirm" class="callout">
          确认用此版本替换当前内容？恢复前会自动备份当前内容。
        </p>
        <BaseButton
          class="full-width"
          @click="restoreConfirm ? doRestore() : (restoreConfirm = true)"
          >{{ restoreConfirm ? '确认恢复此版本' : '恢复这个版本' }}</BaseButton
        ></template
      ></BaseModal
    >
  </div>
  <div v-else-if="loading" class="page-container app-empty">
    <div class="loading-spinner" aria-hidden="true"></div>
    <p>正在加载简历…</p>
  </div>
  <div v-else class="page-container app-empty">
    <h1 class="wrap-heading">没有找到这份简历</h1>
    <p>它可能已被删除，或尚未从服务端加载。</p>
    <BaseButton @click="router.push('/resumes')">返回我的简历</BaseButton>
  </div>
</template>

<style scoped>
.loading-spinner {
  width: 36px;
  height: 36px;
  margin: 0 auto 16px;
  border: 3px solid var(--color-focus-soft);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: editor-spin 0.8s linear infinite;
}
@keyframes editor-spin {
  to {
    transform: rotate(360deg);
  }
}
.editor-tabs button.active {
  background: var(--color-accent);
  color: var(--color-accent-ink);
  border-radius: 10px;
  font-weight: 700;
  box-shadow: 0 3px 10px var(--color-focus-soft);
}
.editor-preview {
  height: calc(100dvh - 250px);
  min-height: 360px !important;
  overflow: hidden !important;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.editor-preview :deep(.server-resume-preview) {
  flex: 1;
  min-height: 0;
}
</style>

<style scoped>
.editor-cards textarea:focus {
  min-height: 220px;
}
</style>

<style scoped>
.module-picker {
  width: min(360px, 100%);
  margin-top: 0;
}
.module-picker-row { padding-top: 10px; }
</style>
<style>
.module-picker-popper .el-cascader-panel {
  max-width: calc(100vw - 32px);
  overflow-x: auto;
}
.module-picker-popper .el-cascader-menu {
  min-width: 140px;
}
</style>
