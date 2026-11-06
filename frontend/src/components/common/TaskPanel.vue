<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import BaseButton from './BaseButton.vue';
import { tasks, waitTask, retryTask, cancelTask } from '../../services/tasks';
import { api, download } from '../../services/client';
import type { Schema } from '../../services/schema';
import { useAppStore } from '../../composables/useAppStore';
const router = useRouter(),
  { refreshData, refreshResume } = useAppStore();
const open = ref(false),
  taskId = ref(''),
  error = ref(''),
  busy = ref(false);
async function run(action: () => Promise<unknown>) {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    await action();
  } catch (e) {
    error.value = e instanceof Error ? e.message : '任务操作失败';
  } finally {
    busy.value = false;
  }
}
async function view(t: Schema<'TaskView'>) {
  if (!t.result) return;
  const r = t.result;
  if (r.resourceType === 'EXPORT') {
    const output = await api<Schema<'ExportOutput'>>(r.resourceUrl);
    await download(`/api/exports/${r.resourceId}/download`, output.fileName);
    return;
  }
  if (r.resourceType === 'PREPARATION_EXPORT') {
    const output = await api<Schema<'PreparationExportOutput'>>(r.resourceUrl);
    await download(
      `/api/preparation-exports/${r.resourceId}/download`,
      `面试准备.${output.format.toLowerCase()}`,
    );
    return;
  }
  if (r.resourceType === 'RESUME') {
    await refreshResume(r.resourceId);
    await router.push(`/resumes/${r.resourceId}/edit`);
  } else if (r.resourceType === 'MATERIAL' || r.resourceType === 'FOLLOWUP_SESSION') {
    throw new Error('该任务所属的制作会话已退出。请从 AI简历生成页面开始新的制作。');
  } else if (r.resourceType === 'JD_VERSION') {
    await refreshData();
    await router.push('/jd-library');
  } else if (r.resourceType === 'PREPARATION') {
    const p = await api<Schema<'PreparationOutput'>>(r.resourceUrl);
    await router.push({
      path: '/interview',
      query: { versionId: p.resumeVersionId, preparationId: p.id },
    });
  } else if (r.resourceType === 'RECOMMENDATION_RUN') {
    await router.push({ path: '/jobs', query: { runId: r.resourceId } });
  } else if (r.resourceType === 'SUGGESTION') {
    const s = await api<{ resumeId: string }>(r.resourceUrl);
    await refreshResume(s.resumeId);
    await router.push(`/resumes/${s.resumeId}/edit`);
  }
  open.value = false;
}
</script>
<template>
  <section class="task-panel">
    <button class="text-link" :aria-expanded="open" @click="open = !open">
      后台任务（{{ tasks.length }}）
    </button>
    <div v-if="open" class="panel">
      <div class="inline-actions">
        <label class="field"
          >查询已有任务 ID<ElInput
            v-model="taskId"
            placeholder="粘贴 taskId，可继续查询已提交的任务"
            aria-label="查询已有任务 ID" /></label
        ><BaseButton
          size="small"
          :loading="busy"
          :disabled="!/^[0-9a-f-]{36}$/.test(taskId)"
          @click="run(() => waitTask(taskId))"
          >查询进度</BaseButton
        >
      </div>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <p v-if="!tasks.length">尚未提交后台任务。</p>
      <article v-for="t in tasks" :key="t.id" class="history-row">
        <div>
          <strong>{{ t.kind }} · {{ t.status }}</strong
          ><small>{{ t.id }} · {{ t.stage }} · 尝试 {{ t.attempt }}</small>
          <p v-if="t.error" class="form-error">{{ t.error.code }}：{{ t.error.message }}</p>
        </div>
        <div class="inline-actions">
          <BaseButton
            v-if="t.status === 'FAILED' && t.error?.canRetry"
            size="small"
            :disabled="busy"
            @click="run(() => retryTask(t))"
            >重试原任务</BaseButton
          ><BaseButton
            v-if="['QUEUED', 'RUNNING'].includes(t.status)"
            size="small"
            variant="secondary"
            :disabled="busy"
            @click="run(() => cancelTask(t))"
            >取消任务</BaseButton
          ><BaseButton
            v-if="t.status === 'SUCCEEDED' && t.result"
            size="small"
            :disabled="busy"
            @click="run(() => view(t))"
            >查看结果 / 下载</BaseButton
          ><BaseButton
            size="small"
            variant="ghost"
            :disabled="busy"
            @click="run(() => waitTask(t.id))"
            >刷新</BaseButton
          >
        </div>
      </article>
    </div>
  </section>
</template>
<style scoped>
.task-panel {
  margin: 10px 28px;
}
.task-panel small {
  display: block;
  overflow-wrap: anywhere;
}
</style>
