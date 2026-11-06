<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { onBeforeRouteLeave, useRoute } from 'vue-router';
import { Download, Save, Sparkles } from '@lucide/vue';
import PageHeading from '../components/common/PageHeading.vue';
import BaseButton from '../components/common/BaseButton.vue';
import { useAppStore } from '../composables/useAppStore';
import { api, allPages, download } from '../services/client';
import { waitTask, resource } from '../services/tasks';
import type { Schema } from '../services/schema';
const { state, snapshot } = useAppStore();
const route = useRoute();
const resumeId = ref(state.resumes[0]?.id ?? ''),
  versionId = ref(''),
  activeId = ref('');
const type = ref<'INTRODUCTION' | 'INTERVIEW_QUESTIONS'>('INTRODUCTION'),
  tone = ref('自然简洁'),
  count = ref(5);
const list = ref<Schema<'PreparationOutput'>[]>([]),
  active = ref<Schema<'PreparationOutput'> | null>(null);
const saved = ref(''),
  error = ref(''),
  busy = ref(false),
  format = ref<'DOCX' | 'PDF'>('DOCX');
const dirty = computed(
  () => !!active.value && JSON.stringify(active.value.content) !== saved.value,
);
function select(p: Schema<'PreparationOutput'>) {
  active.value = JSON.parse(JSON.stringify(p));
  activeId.value = p.id;
  saved.value = JSON.stringify(p.content);
}
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
async function load() {
  if (!versionId.value) {
    list.value = [];
    active.value = null;
    return;
  }
  list.value = await allPages<Schema<'PreparationOutput'>>(
    `/api/preparations?resumeVersionId=${versionId.value}`,
  );
  const chosen = list.value.find((p) => p.id === activeId.value) ?? list.value[0];
  if (chosen) select(chosen);
  else active.value = null;
}
watch(versionId, () => {
  if (!busy.value) void run(load);
});
if (typeof route.query.versionId === 'string') {
  const v = state.versions.find((v) => v.id === route.query.versionId);
  if (v) {
    resumeId.value = v.resumeId;
    versionId.value = v.id;
    activeId.value = typeof route.query.preparationId === 'string' ? route.query.preparationId : '';
    void run(load);
  }
}
watch(resumeId, () => {
  versionId.value = '';
  list.value = [];
  active.value = null;
});
async function generate() {
  await run(async () => {
    const resume = state.resumes.find((r) => r.id === resumeId.value);
    if (!resume) throw new Error('请选择一份简历');
    if (dirty.value) throw new Error('请先保存正在编辑的资料');
    const version = await snapshot(resume, '面试准备使用版本');
    versionId.value = version.id;
    const accepted = await api<Schema<'AsyncAccepted'>>('/api/preparations', 'POST', {
      resumeVersionId: version.id,
      type: type.value,
      ...(type.value === 'INTERVIEW_QUESTIONS' ? { questionCount: count.value } : {}),
      tone: tone.value,
    });
    activeId.value = accepted.resourceId;
    const p = await resource<Schema<'PreparationOutput'>>(accepted);
    await load();
    select(p);
  });
}
async function save() {
  if (!active.value) return;
  const result = await api<Schema<'PreparationOutput'>>(
    `/api/preparations/${active.value.id}`,
    'PATCH',
    { baseRevision: active.value.revision, content: active.value.content },
  );
  select(result);
  const i = list.value.findIndex((p) => p.id === result.id);
  if (i >= 0) list.value[i] = result;
}
async function exportMaterials() {
  await run(async () => {
    if (!active.value) throw new Error('请选择已生成的资料');
    if (dirty.value) await save();
    const accepted = await api<Schema<'AsyncAccepted'>>(
      `/api/preparations/${active.value.id}/exports`,
      'POST',
      { baseRevision: active.value.revision, format: format.value },
    );
    await waitTask(accepted.taskId);
    await download(
      `/api/preparation-exports/${accepted.resourceId}/download`,
      `${active.value.type === 'INTRODUCTION' ? '自我介绍' : '面试问答'}.${format.value.toLowerCase()}`,
    );
  });
}
onBeforeRouteLeave(
  () => !dirty.value || window.confirm('面试资料尚未保存，确定离开并放弃本次修改吗？'),
);
</script>
<template>
  <div class="page-container">
    <PageHeading
      eyebrow="PREPARE FOR YOUR MOMENT"
      title="面试准备"
      description=""
    />
    <div class="panel">
      <div class="form-grid">
        <label class="field"
          >简历<ElSelect v-model="resumeId" :disabled="dirty" aria-label="简历"
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
      <BaseButton :loading="busy" :disabled="dirty" @click="generate"
        ><Sparkles :size="16" />生成新资料</BaseButton
      >
      <p>生成新资料会保留之前的资料。后端尚未提供的个人练习回答和删除功能已隐藏。</p>
    </div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div class="interview-grid">
      <aside class="panel">
        <h2>面试准备资料</h2>
        <BaseButton variant="ghost" :disabled="busy || dirty" @click="run(load)"
          >刷新列表</BaseButton
        ><button
          v-for="p in list"
          :key="p.id"
          class="history-row"
          :disabled="dirty || busy"
          @click="select(p)"
        >
          <span
            >{{ p.type === 'INTRODUCTION' ? '自我介绍' : '面试问答' }} · {{ p.status
            }}<small>{{ p.createdAt }}</small></span
          >
        </button>
      </aside>
      <section v-if="active" class="panel">
        <h2>{{ active.type === 'INTRODUCTION' ? '自我介绍' : '面试问答' }}</h2>
        <p>
          状态：{{ active.status }} / 修订 {{ active.revision }}
          <strong v-if="dirty">· 有未保存修改</strong>
        </p>
        <p v-if="active.isOutdated" class="callout">简历已更新，本资料仍对应生成时的历史版本。</p>
        <template v-if="active.status === 'READY'"
          ><label v-if="active.content.introduction !== null" class="field"
            >自我介绍<ElInput
              v-model="active.content.introduction"
              :rows="8"
              type="textarea"
              aria-label="自我介绍"
            />
          </label>
          <details v-for="q in active.content.questions" :key="q.id" class="question-detail" open>
            <summary>{{ q.number }}. {{ q.question }}</summary>
            <label class="field"
              >问题<ElInput
                v-model="q.question"
                :rows="2"
                type="textarea"
                aria-label="问题" /></label
            ><label class="field"
              >参考回答<ElInput
                v-model="q.referenceAnswer"
                :rows="5"
                type="textarea"
                aria-label="参考回答"
            /></label>
            <p v-if="q.missingFacts.length">待补充事实：{{ q.missingFacts.join('；') }}</p>
          </details>
          <div class="inline-actions">
            <BaseButton :loading="busy" :disabled="!dirty" @click="run(save)"
              ><Save :size="16" />保存修改</BaseButton
            ><label class="field"
              >导出格式<ElSelect v-model="format" aria-label="导出格式"
                ><ElOption :value="'DOCX'" :label="'DOCX'" />
                <ElOption :value="'PDF'" :label="'PDF'" /></ElSelect></label
            ><BaseButton variant="secondary" :loading="busy" @click="exportMaterials"
              ><Download :size="16" />后端生成并下载</BaseButton
            >
          </div></template
        >
        <p v-else>任务未完成或失败，请查看任务面板，成功后刷新资料列表。</p>
      </section>
      <section v-else class="panel app-empty">选择简历并生成一份新的准备资料。</section>
    </div>
  </div>
</template>
