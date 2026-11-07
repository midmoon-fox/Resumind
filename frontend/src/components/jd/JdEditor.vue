<script setup lang="ts">
import { ref, watch } from 'vue';
import { Upload, X } from '@lucide/vue';
import FileUpload from '../common/FileUpload.vue';
import BaseButton from '../common/BaseButton.vue';
import { useAppStore } from '../../composables/useAppStore';
import { api, uploadFile } from '../../services/client';
import { resource, waitTask } from '../../services/tasks';
import { archiveTitle } from '../../services/jd';
import type { Schema } from '../../services/schema';
import type { JobDescription } from '../../types/app';
const props = defineProps<{
  direction?: string;
  draftOnly?: boolean;
  initialText?: string;
  initialFile?: File | null;
}>();
const emit = defineEmits<{
  saved: [id: string];
  busy: [value: boolean];
  draft: [value: { text: string; file: File | null }];
}>();
const { refreshData } = useAppStore();
const busy = ref(false),
  error = ref(''),
  localDirection = ref('');
const selectedFile = ref<File | null>(props.initialFile || null);
const selected = ref<JobDescription | null>(null);
const version = ref<Schema<'JdVersionOut'> | null>(null);
const form = ref({ text: props.initialText || '' });
watch(
  () => [form.value.text, selectedFile.value] as const,
  ([text, file]) => emit('draft', { text, file }),
);
watch(busy, (value) => emit('busy', value), { flush: 'sync' });
async function run(action: () => Promise<void>) {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    await action();
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败，请重试';
  } finally {
    busy.value = false;
  }
}
async function persist(v: Schema<'JdVersionOut'>) {
  const jd = await api<Schema<'JdOut'>>(`/api/job-descriptions/${v.jdId}`);
  if (v.status === 'REVIEW_REQUIRED') {
    version.value = await api<Schema<'JdVersionOut'>>(
      `/api/job-descriptions/${v.jdId}/confirmations`,
      'POST',
      {
        baseRevision: jd.revision,
        jdVersionId: v.id,
        title: jd.title,
        originalText: v.originalText,
        jobTitle: v.jobTitle,
        companyName: v.companyName,
        requirements: v.requirements,
      },
    );
  } else if (v.status !== 'CONFIRMED')
    throw new Error('JD 尚未分析成功，请重新分析或在后台任务中重试');
  await refreshData();
}
async function load(j: JobDescription) {
  selected.value = j;
  form.value.text = j.text;
  selectedFile.value = null;
  await run(async () => {
    let v = await api<Schema<'JdVersionOut'>>(
      `/api/job-descriptions/${j.id}/versions/${j.backend!.currentVersionId}`,
    );
    if (['QUEUED', 'ANALYZING'].includes(v.status)) {
      await waitTask(v.taskId);
      v = await api<Schema<'JdVersionOut'>>(`/api/job-descriptions/${j.id}/versions/${v.id}`);
    }
    version.value = v;
    form.value.text = v.originalText;
    if (['REVIEW_REQUIRED', 'CONFIRMED'].includes(v.status)) await persist(v);
  });
}
async function analyze() {
  let savedId: string | undefined;
  await run(async () => {
    const text = form.value.text.trim();
    if (!text && !selectedFile.value) throw new Error('请填写 JD 原文或选择文件，至少提供一项');
    const file = selectedFile.value ? await uploadFile(selectedFile.value, 'JD') : null;
    let accepted: Schema<'AsyncAccepted'>;
    if (selected.value) {
      const jd = await api<Schema<'JdOut'>>(`/api/job-descriptions/${selected.value.id}`);
      accepted = await api(`/api/job-descriptions/${jd.id}/versions`, 'POST', {
        baseRevision: jd.revision,
        ...(file ? { fileId: file.id } : {}),
        ...(text ? { originalText: text } : {}),
      });
    } else
      accepted = await api('/api/job-descriptions', 'POST', {
        title: archiveTitle(props.direction || localDirection.value),
        ...(file ? { fileId: file.id } : {}),
        ...(text ? { text } : {}),
      });
    version.value = await resource<Schema<'JdVersionOut'>>(accepted);
    await persist(version.value);
    selectedFile.value = null;
    savedId = version.value.jdId;
  });
  if (savedId) emit('saved', savedId);
}
function choose(files: File[]) {
  error.value = '';
  const file = files[0];
  if (!file) return;
  if (!/\.(txt|jpe?g|png)$/i.test(file.name)) {
    error.value = '岗位 JD 仅支持 TXT、JPG、PNG 文件';
    return;
  }
  if (file.size > 20 * 1024 * 1024) {
    error.value = '文件不能超过 20MB';
    return;
  }
  selectedFile.value = file;
}
defineExpose({ load, busy });
</script>
<template>
  <div class="jd-editor" :aria-busy="busy">
    <label v-if="props.direction === undefined && !selected" class="field"
      >求职方向
      <ElInput
        v-model="localDirection"
        maxlength="100"
        aria-label="求职方向"
        placeholder="例如：前端开发工程师"
        :disabled="busy"
      />
    </label>
    <p class="field-hint">
      档案名称按求职方向和时间自动生成。文件和原文至少提供一项，同时提供会合并分析。
    </p>
    <FileUpload
      drag
      class="jd-upload"
      accept=".txt,.jpg,.jpeg,.png"
      :disabled="busy"
      @select="choose"
    >
      <strong>点击选择或拖入岗位文件</strong>
      <small>TXT / JPG / PNG · 单个 20MB 以内</small>
      <span class="jd-upload-card"><Upload :size="25" /></span>
    </FileUpload>
    <div v-if="selectedFile" class="attachment-row">
      <span>{{ selectedFile.name }}</span>
      <button
        class="icon-button"
        aria-label="移除 JD 文件"
        :disabled="busy"
        @click="selectedFile = null"
      >
        <X :size="16" />
      </button>
    </div>
    <label class="field"
      >JD 原文
      <ElInput
        v-model="form.text"
        :rows="6"
        maxlength="100000"
        type="textarea"
        aria-label="JD 原文"
        placeholder="粘贴岗位职责、任职要求等原文；已选文件时，也可补充岗位说明。"
        :disabled="busy"
      />
    </label>
    <BaseButton v-if="!draftOnly" :loading="busy" @click="analyze">{{
      selected ? '重新分析并保存' : '分析并保存'
    }}</BaseButton>
    <p v-if="version?.status === 'CONFIRMED' && !busy" class="field-hint">
      JD 已保存，可以用于制作简历。
    </p>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
  </div>
</template>
<style scoped>
.jd-editor {
  min-width: 0;
}
.jd-review {
  padding: 0;
  margin: 20px 0 0;
  border: 0;
  min-width: 0;
}
.jd-upload {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border-color, #dedbed);
  border-radius: 18px;
  margin: 16px 0;
  perspective: 800px;
  background:
    linear-gradient(#d1d0ef33 1px, transparent 1px),
    linear-gradient(90deg, #d1d0ef33 1px, transparent 1px);
  background-size: 22px 22px;
}
.jd-upload :deep(.el-upload) {
  width: 100%;
}
.jd-upload :deep(.el-upload-dragger) {
  border: 0;
  background: transparent;
  border-radius: 18px;
}
.jd-upload :deep(.el-upload-dragger) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 28px 16px;
  text-align: center;
}
.jd-upload small {
  color: var(--text-secondary, #716b83);
}
.jd-upload-card {
  display: grid;
  place-items: center;
  width: 88px;
  height: 88px;
  margin-top: 8px;
  border: 1px solid #dedbed;
  border-radius: 16px;
  background: #ffffffeb;
  color: #7353d9;
  box-shadow: 0 5px 18px #30214b12;
  transition:
    transform 0.3s,
    box-shadow 0.3s;
}
.jd-upload:is(:hover, :focus-within) .jd-upload-card {
  transform: translateY(-6px) rotateX(10deg) rotateY(-8deg);
  box-shadow: 0 12px 24px #7353d926;
}
@media (prefers-reduced-motion: reduce) {
  .jd-upload-card {
    transition: none;
    transform: none !important;
  }
}
</style>
