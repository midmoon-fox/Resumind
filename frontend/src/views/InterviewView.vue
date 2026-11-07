<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave, useRoute } from 'vue-router';
import { ChevronRight, Download, Save, Sparkles, Trash2 } from '@lucide/vue';
import { ElMessageBox } from 'element-plus';
import PageHeading from '../components/common/PageHeading.vue';
import BaseButton from '../components/common/BaseButton.vue';
import BaseModal from '../components/common/BaseModal.vue';
import { useAppStore } from '../composables/useAppStore';
import { api, allPages, download } from '../services/client';
import { waitTask, resource, retryTask, tasks } from '../services/tasks';
import type { Schema } from '../services/schema';
const { state, snapshot } = useAppStore();
const route = useRoute();
const linkedVersion = state.versions.find((v) => v.id === route.query.versionId);
const resumeId = ref(linkedVersion?.resumeId ?? state.resumes[0]?.id ?? '');
const openResumeId = ref(resumeId.value);
const type = ref<'INTRODUCTION' | 'INTERVIEW_QUESTIONS'>('INTRODUCTION'),
  tone = ref('自然简洁'),
  count = ref(5);
type Preparation = Schema<'PreparationOutput'>;
const list = ref<Preparation[]>([]);
const active = ref<Preparation | null>(null);
const draft = ref<Preparation['content'] | null>(null);
const resumeByVersion = computed(() => new Map(state.versions.map((v) => [v.id, v.resumeId])));
const dayFormat = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  timeZone: 'Asia/Shanghai',
});
const timeFormat = new Intl.DateTimeFormat('zh-CN', {
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
  timeZone: 'Asia/Shanghai',
});
const historyGroups = computed(() => {
  const byResume = new Map<string, Map<string, Preparation[]>>();
  const ordered = [...list.value].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt));
  for (const preparation of ordered) {
    const id = resumeByVersion.value.get(preparation.resumeVersionId);
    if (!id) continue;
    const days = byResume.get(id) ?? new Map<string, Preparation[]>();
    const day = dayFormat.format(new Date(preparation.createdAt));
    const entries = days.get(day) ?? [];
    entries.push(preparation);
    days.set(day, entries);
    byResume.set(id, days);
  }
  return state.resumes.flatMap((resume) => {
    const days = byResume.get(resume.id);
    if (!days) return [];
    const dates = [...days].map(([date, entries]) => ({ date, entries }));
    return [
      {
        id: resume.id,
        title: resume.title,
        dates,
        count: dates.reduce((n, d) => n + d.entries.length, 0),
      },
    ];
  });
});
const error = ref(''),
  busy = ref(false);
const generation = ref<Schema<'AsyncAccepted'> | null>(null);
const retryableGeneration = computed(() =>
  tasks.find(
    (task) =>
      task.id === generation.value?.taskId && task.status === 'FAILED' && task.error?.canRetry,
  ),
);
const exportOpen = ref(false),
  exportName = ref(''),
  format = ref<'DOCX' | 'PDF'>('DOCX');
const fileStem = computed(() =>
  exportName.value
    .trim()
    .replace(/(?:\.(?:pdf|docx))+$/i, '')
    .trim(),
);
function select(preparation: Preparation) {
  active.value = preparation;
  const parentId = resumeByVersion.value.get(preparation.resumeVersionId);
  if (parentId) {
    openResumeId.value = parentId;
    resumeId.value = parentId;
  }
}
function editPreparation() {
  if (active.value?.status === 'READY') {
    draft.value = JSON.parse(JSON.stringify(active.value.content));
  }
}
async function savePreparation() {
  if (!active.value || !draft.value) return;
  const { id, revision } = active.value;
  await run(async () => {
    const saved = await api<Preparation>(`/api/preparations/${id}`, 'PATCH', {
      baseRevision: revision,
      content: draft.value,
    });
    list.value = list.value.map((item) => (item.id === saved.id ? saved : item));
    select(saved);
    draft.value = null;
  });
}
onBeforeRouteLeave(() => !draft.value || window.confirm('确定放弃本次面试资料编辑并离开吗？'));
async function run(action: () => Promise<void>) {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    await action();
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败';
  } finally {
    busy.value = false;
  }
}
async function load(preferredId = active.value?.id ?? route.query.preparationId) {
  const resumeIds = new Set(state.resumes.map((resume) => resume.id));
  const versions = state.versions.filter((version) => resumeIds.has(version.resumeId));
  const rows: Preparation[] = [];
  // The preparation endpoint lists one fixed resume version at a time.
  for (let index = 0; index < versions.length; index += 6) {
    const pages = await Promise.all(
      versions
        .slice(index, index + 6)
        .map((version) => allPages<Preparation>(`/api/preparations?resumeVersionId=${version.id}`)),
    );
    rows.push(...pages.flat());
  }
  list.value = rows;
  const chosen =
    list.value.find((p) => p.id === preferredId) ??
    list.value.find((p) => p.resumeVersionId === route.query.versionId) ??
    historyGroups.value.find((group) => group.id === resumeId.value)?.dates[0]?.entries[0] ??
    historyGroups.value[0]?.dates[0]?.entries[0];
  if (chosen) select(chosen);
  else active.value = null;
}
onMounted(() => void run(load));
watch(
  () => route.query.preparationId,
  (id) => {
    if (draft.value) return;
    const preparation = list.value.find((p) => p.id === id);
    if (preparation) select(preparation);
    else if (typeof id === 'string') void run(() => load(id));
  },
);
async function generate() {
  await run(async () => {
    generation.value = null;
    const resume = state.resumes.find((r) => r.id === resumeId.value);
    if (!resume) throw new Error('请选择一份简历');
    const version = await snapshot(resume, '面试准备使用版本');
    const accepted = await api<Schema<'AsyncAccepted'>>('/api/preparations', 'POST', {
      resumeVersionId: version.id,
      type: type.value,
      ...(type.value === 'INTERVIEW_QUESTIONS' ? { questionCount: count.value } : {}),
      tone: tone.value,
    });
    generation.value = accepted;
    showGenerated(await resource<Preparation>(accepted));
  });
}
function showGenerated(preparation: Preparation) {
  if (preparation.status !== 'READY') throw new Error('资料尚未生成成功');
  list.value = [preparation, ...list.value.filter((item) => item.id !== preparation.id)];
  select(preparation);
  generation.value = null;
}
async function retryGeneration(taskId: string, resourceUrl: string) {
  await run(async () => {
    const task = await api<Schema<'TaskView'>>(`/api/tasks/${taskId}`);
    if (task.status !== 'FAILED' || !task.error?.canRetry) {
      throw new Error(task.error?.message ?? '该任务当前无法重试，请刷新资料列表');
    }
    await retryTask(task);
    showGenerated(await api<Preparation>(resourceUrl));
  });
}
async function deletePreparation(preparation: Preparation) {
  const label = preparation.type === 'INTRODUCTION' ? '自我介绍' : '面试问答';
  try {
    await ElMessageBox.confirm(
      `删除这份${label}？删除后无法再查看资料或下载关联的导出文件。`,
      '删除面试资料',
      {
        type: 'warning',
        customClass: 'preparation-delete-confirm',
        // The document keeps its scrollbar, so compensating for it would shrink the page.
        lockScroll: false,
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    );
  } catch {
    return;
  }
  await run(async () => {
    await api<void>(`/api/preparations/${preparation.id}`, 'DELETE');
    list.value = list.value.filter((item) => item.id !== preparation.id);
    if (active.value?.id !== preparation.id) return;
    const parentId = resumeByVersion.value.get(preparation.resumeVersionId);
    const next =
      historyGroups.value.find((group) => group.id === parentId)?.dates[0]?.entries[0] ??
      historyGroups.value[0]?.dates[0]?.entries[0];
    if (next) select(next);
    else active.value = null;
  });
}
function openExport() {
  if (busy.value || draft.value || active.value?.status !== 'READY') return;
  error.value = '';
  exportName.value = active.value.type === 'INTRODUCTION' ? '自我介绍' : '面试问答';
  exportOpen.value = true;
}
function closeExport() {
  if (!busy.value) exportOpen.value = false;
}
async function exportMaterials() {
  const preparation = active.value;
  const stem = fileStem.value;
  const fileFormat = format.value;
  if (!exportOpen.value || preparation?.status !== 'READY' || !stem) return;
  await run(async () => {
    const accepted = await api<Schema<'AsyncAccepted'>>(
      `/api/preparations/${preparation.id}/exports`,
      'POST',
      { baseRevision: preparation.revision, format: fileFormat, fileName: stem },
    );
    await waitTask(accepted.taskId);
    await download(
      `/api/preparation-exports/${accepted.resourceId}/download`,
      `${stem}.${fileFormat.toLowerCase()}`,
    );
    exportOpen.value = false;
  });
}
</script>
<template>
  <div class="page-container">
    <PageHeading eyebrow="PREPARE FOR YOUR MOMENT" title="面试准备" description="" />
    <div class="panel">
      <div class="form-grid">
        <label class="field"
          >简历<ElSelect v-model="resumeId" aria-label="简历"
            ><ElOption value="" :label="'请选择'" />
            <ElOption
              v-for="r in state.resumes"
              :key="r.id"
              :value="r.id"
              :label="String(r.title)" /></ElSelect></label
        ><label class="field"
          >资料类型<ElSelect v-model="type" aria-label="资料类型"
            ><ElOption value="INTRODUCTION" :label="'自我介绍'" />
            <ElOption value="INTERVIEW_QUESTIONS" :label="'面试问答'" /></ElSelect></label
        ><label class="field"
          >表达风格<ElInput v-model="tone" maxlength="100" aria-label="表达风格" /></label
        ><label v-if="type === 'INTERVIEW_QUESTIONS'" class="field"
          >题数<ElSelect v-model="count" aria-label="题数"
            ><ElOption v-for="n in 6" :key="n" :value="n + 4" :label="String(n + 4)" /></ElSelect
        ></label>
      </div>
      <BaseButton :loading="busy" :disabled="!!draft" @click="generate"
        ><Sparkles :size="16" />生成新资料</BaseButton
      >
      <p>生成新资料会保留之前的资料。</p>
    </div>
    <div v-if="error && !exportOpen" class="inline-actions">
      <p class="form-error" role="alert">{{ error }}</p>
      <BaseButton
        v-if="retryableGeneration && generation"
        variant="secondary"
        size="small"
        :disabled="busy || !!draft"
        @click="retryGeneration(generation.taskId, generation.resourceUrl)"
      >
        重试本次生成
      </BaseButton>
    </div>
    <div class="interview-grid">
      <aside class="panel preparation-history">
        <h2>面试准备资料</h2>
        <BaseButton variant="ghost" :disabled="busy || !!draft" @click="run(load)"
          >刷新列表</BaseButton
        >
        <p v-if="!historyGroups.length" class="history-empty">
          {{ busy ? '正在加载资料…' : '暂无面试准备资料' }}
        </p>
        <details
          v-for="group in historyGroups"
          :key="group.id"
          class="history-group"
          :open="group.id === openResumeId"
        >
          <summary class="history-group-heading">
            <ChevronRight :size="14" aria-hidden="true" />
            <strong>{{ group.title }}</strong>
            <small>{{ group.count }} 份</small>
          </summary>
          <ol class="history-timeline">
            <li v-for="day in group.dates" :key="day.date" class="history-day">
              <div class="history-date">{{ day.date }}</div>
              <div
                v-for="preparation in day.entries"
                :key="preparation.id"
                class="history-entry-row"
              >
                <button
                  type="button"
                  class="history-entry"
                  :aria-pressed="active?.id === preparation.id"
                  :disabled="busy || !!draft"
                  @click="select(preparation)"
                >
                  <time :datetime="preparation.createdAt">{{
                    timeFormat.format(new Date(preparation.createdAt))
                  }}</time>
                  <span>{{ preparation.type === 'INTRODUCTION' ? '自我介绍' : '面试问答' }}</span>
                </button>
                <button
                  type="button"
                  class="history-delete"
                  aria-label="删除这份资料"
                  :disabled="busy || !!draft || preparation.status === 'GENERATING'"
                  @click="deletePreparation(preparation)"
                >
                  <Trash2 :size="15" aria-hidden="true" />
                </button>
              </div>
            </li>
          </ol>
        </details>
      </aside>
      <section v-if="active" class="panel">
        <h2>{{ active.type === 'INTRODUCTION' ? '自我介绍' : '面试问答' }}</h2>
        <p v-if="active.isOutdated" class="callout">简历已更新，本资料仍对应生成时的历史版本。</p>
        <template v-if="active.status === 'READY'">
          <template v-if="draft">
            <label v-if="draft.introduction !== null" class="field">
              自我介绍
              <ElInput v-model="draft.introduction" type="textarea" :rows="8" :disabled="busy" />
            </label>
            <details v-for="q in draft.questions" :key="q.id" class="question-detail" open>
              <summary>第 {{ q.number }} 题</summary>
              <label class="field">
                问题
                <ElInput v-model="q.question" type="textarea" :rows="2" :disabled="busy" />
              </label>
              <label class="field">
                参考回答
                <ElInput v-model="q.referenceAnswer" type="textarea" :rows="5" :disabled="busy" />
              </label>
            </details>
            <div class="inline-actions">
              <BaseButton :loading="busy" @click="savePreparation"
                ><Save :size="16" />保存修改</BaseButton
              >
              <BaseButton variant="secondary" :disabled="busy" @click="draft = null"
                >取消编辑</BaseButton
              >
            </div>
          </template>
          <template v-else>
            <p v-if="active.type === 'INTRODUCTION'" class="preparation-prose">
              {{ active.content.introduction }}
            </p>
            <details v-for="q in active.content.questions" :key="q.id" class="question-detail" open>
              <summary>{{ q.number }}. {{ q.question }}</summary>
              <div class="answer-example">
                <strong>回答范例</strong>
                <p class="preparation-prose">{{ q.referenceAnswer }}</p>
              </div>
              <p v-if="q.missingFacts.length">待补充事实：{{ q.missingFacts.join('；') }}</p>
            </details>
            <div class="inline-actions">
              <BaseButton variant="secondary" :disabled="busy" @click="editPreparation"
                >编辑资料</BaseButton
              >
              <BaseButton variant="secondary" :disabled="busy" @click="openExport">
                <Download :size="16" />后端生成并下载
              </BaseButton>
            </div>
          </template>
        </template>
        <div v-else-if="active.status === 'FAILED'">
          <p>资料生成未完成，可重试或删除这份记录。</p>
          <BaseButton
            variant="secondary"
            :disabled="busy"
            @click="retryGeneration(active.taskId, `/api/preparations/${active.id}`)"
            >重试生成</BaseButton
          >
        </div>
        <p v-else>资料仍在生成，稍后可刷新列表查看。</p>
      </section>
      <section v-else class="panel app-empty">选择简历并生成一份新的准备资料。</section>
    </div>
    <BaseModal :open="exportOpen" title="导出面试资料" @close="closeExport">
      <form @submit.prevent="exportMaterials">
        <label class="field">
          导出格式
          <ElSelect v-model="format" :disabled="busy" aria-label="导出格式">
            <ElOption value="PDF" label="PDF" />
            <ElOption value="DOCX" label="DOCX" />
          </ElSelect>
        </label>
        <label class="field">
          文件名称
          <ElInput v-model="exportName" :disabled="busy" maxlength="100" aria-label="文件名称" />
        </label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <div class="modal-actions">
          <BaseButton variant="secondary" :disabled="busy" @click="closeExport">取消</BaseButton>
          <BaseButton type="submit" :loading="busy" :disabled="!fileStem || busy">
            <Download :size="16" />{{ busy ? '正在生成…' : '生成并下载' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>
  </div>
</template>

<style scoped>
:global(.preparation-delete-confirm .el-message-box__btns) {
  column-gap: 8px;
}
.history-empty,
.history-group-heading small,
.history-date,
.history-entry time {
  color: var(--color-muted);
  font-size: var(--text-xs);
}
.history-group + .history-group {
  border-top: 1px solid var(--color-rule);
}
.history-group-heading {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 0;
  list-style: none;
  cursor: pointer;
}
.history-group-heading::-webkit-details-marker {
  display: none;
}
.history-group-heading svg,
.history-group-heading small {
  flex-shrink: 0;
}
.history-group[open] .history-group-heading svg {
  transform: rotate(90deg);
}
.history-group-heading strong {
  min-width: 0;
  overflow-wrap: anywhere;
}
.history-group-heading small {
  margin-left: auto;
}
.history-timeline {
  list-style: none;
  margin: 0 0 8px 7px;
  padding: 0 0 0 11px;
  border-left: 1px solid var(--color-rule);
}
.history-day + .history-day {
  margin-top: 10px;
}
.history-date {
  position: relative;
  margin-bottom: 4px;
}
.history-date::before {
  position: absolute;
  top: 0.45em;
  left: -15px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-accent);
  content: '';
}
.history-entry-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}
.history-delete {
  display: inline-grid;
  place-items: center;
  width: 32px;
  min-height: 32px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
}
.history-delete:not(:disabled):hover {
  background: var(--color-accent-soft);
  color: var(--color-ink);
}
.history-delete:disabled {
  cursor: default;
  visibility: hidden;
}
@media (hover: hover) and (pointer: fine) {
  .history-delete {
    opacity: 0;
  }
  .history-entry-row:hover .history-delete,
  .history-entry-row:focus-within .history-delete {
    opacity: 1;
  }
}
.history-entry {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 7px 6px;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.history-entry time {
  font-variant-numeric: tabular-nums;
}
.history-entry:hover,
.history-entry[aria-pressed='true'] {
  background: var(--color-accent-soft);
}
.history-entry[aria-pressed='true'] {
  color: var(--color-accent);
  font-weight: 600;
}
.history-entry:disabled {
  cursor: default;
}
.answer-example {
  margin-top: var(--space-sm);
}
.preparation-prose {
  margin-top: var(--space-xs);
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
