<script setup lang="ts">
import { computed, ref, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { ArrowRight, Plus, Search, Trash2, FileText } from '@lucide/vue';
import JdEditor from '../components/jd/JdEditor.vue';
import PageHeading from '../components/common/PageHeading.vue';
import BaseButton from '../components/common/BaseButton.vue';
import BaseModal from '../components/common/BaseModal.vue';
import { useAppStore } from '../composables/useAppStore';
import { api } from '../services/client';
import type { Schema } from '../services/schema';
import type { JobDescription } from '../types/app';
const { state, refreshData } = useAppStore(),
  router = useRouter();
const search = ref(''),
  open = ref(false),
  busy = ref(false),
  error = ref('');
const editor = ref<InstanceType<typeof JdEditor>>();
const editorKey = ref(0);
const impact = ref<Schema<'Impact'> | null>(null);
const list = computed(() =>
  state.jds.filter((j) =>
    (j.title + j.company + j.text).toLowerCase().includes(search.value.trim().toLowerCase()),
  ),
);
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
function add() {
  editorKey.value++;
  error.value = '';
  open.value = true;
}
async function details(j: JobDescription) {
  add();
  await nextTick();
  await editor.value?.load(j);
}
async function useJd(j: JobDescription) {
  await run(async () => {
    if (j.version?.status !== 'CONFIRMED') throw new Error('请先打开 JD，完成分析并保存');
    await router.push({ path: '/create', query: { jdId: j.id } });
  });
}
async function remove(j: JobDescription) {
  await run(async () => {
    impact.value = await api<Schema<'Impact'>>(`/api/job-descriptions/${j.id}/deletion-impact`);
  });
}
async function confirmRemove() {
  await run(async () => {
    const id = impact.value!.resourceId;
    await api(`/api/job-descriptions/${id}`, 'DELETE');
    if (state.workspace.jdId === id) {
      state.workspace.jdId = '';
      if (state.workspace.backend)
        state.workspace.backend = await api<Schema<'WorkspaceOut'>>(
          `/api/workspaces/${state.workspace.backend.id}`,
        );
    }
    impact.value = null;
    await refreshData();
  });
}
</script>
<template>
  <div class="page-container">
    <PageHeading
      eyebrow="JOB DESCRIPTION LIBRARY"
      title="岗位需求档案"
      description=""
      ><BaseButton @click="add"><Plus :size="17" />新增岗位需求档案</BaseButton></PageHeading
    >
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div class="panel">
      <div class="list-toolbar">
        <h2>全部档案 {{ list.length }}</h2>
        <label class="inline-search"
          ><Search :size="16" /><ElInput
            v-model="search"
            aria-label="搜索岗位需求档案"
            placeholder="搜索岗位需求档案或公司"
        /></label>
      </div>
      <div v-if="list.length" class="jd-list">
        <article v-for="j in list" :key="j.id" class="jd-row">
          <FileText :size="24" />
          <div class="jd-summary">
            <h2>{{ j.title }}</h2>
            <p>{{ j.company }} · {{ j.version?.status }}</p>
            <p>{{ j.text.slice(0, 120) }}</p>
          </div>
          <div class="inline-actions">
            <BaseButton size="small" variant="secondary" :disabled="busy" @click="details(j)"
              >查看 / 编辑</BaseButton
            ><BaseButton
              size="small"
              :disabled="busy || j.version?.status !== 'CONFIRMED'"
              @click="useJd(j)"
              >用于简历<ArrowRight :size="15" /></BaseButton
            ><button
              class="icon-button danger-icon"
              :aria-label="'删除' + j.title"
              @click="remove(j)"
            >
              <Trash2 :size="16" />
            </button>
          </div>
        </article>
      </div>
      <p v-else class="app-empty">还没有 JD 档案。添加原文或岗位截图后开始分析。</p>
    </div>
    <BaseModal :open="open" title="岗位 JD" wide @close="!busy && (open = false)">
      <JdEditor
        v-if="open"
        :key="editorKey"
        ref="editor"
        @busy="busy = $event"
        @saved="open = false"
      />
    </BaseModal>
    <BaseModal :open="!!impact" title="确认删除 JD？" @close="impact = null"
      ><p v-for="m in impact?.messages" :key="m">{{ m }}</p>
      <p>关联资源数量：{{ impact?.affectedCounts }}</p>
      <BaseButton :loading="busy" @click="confirmRemove">确认删除</BaseButton></BaseModal
    >
  </div>
</template>

<style scoped>

</style>