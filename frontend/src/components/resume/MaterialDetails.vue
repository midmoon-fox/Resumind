<script setup lang="ts">
import { ref } from 'vue';
import BaseModal from '../common/BaseModal.vue';
import BaseButton from '../common/BaseButton.vue';
import { api, allPages, download } from '../../services/client';
import type { Schema } from '../../services/schema';
const props = defineProps<{ materialId: string }>();
const open = ref(false),
  error = ref(''),
  busy = ref(false);
const material = ref<Schema<'MaterialOut'> | null>(null),
  segments = ref<Schema<'SegmentOut'>[]>([]);
async function load() {
  open.value = true;
  busy.value = true;
  error.value = '';
  try {
    material.value = await api<Schema<'MaterialOut'>>(`/api/materials/${props.materialId}`);
    segments.value = await allPages<Schema<'SegmentOut'>>(
      `/api/materials/${props.materialId}/segments`,
    );
  } catch (e) {
    error.value = e instanceof Error ? e.message : '材料读取失败';
  } finally {
    busy.value = false;
  }
}
async function original() {
  try {
    if (material.value?.fileId)
      await download(`/api/files/${material.value.fileId}/download`, material.value.title);
  } catch (e) {
    error.value = e instanceof Error ? e.message : '下载失败';
  }
}
</script>
<template>
  <BaseButton size="small" variant="ghost" @click="load">原文 / 状态</BaseButton
  ><BaseModal :open="open" title="材料原文与提取状态" wide @close="open = false"
    ><p v-if="busy">正在读取…</p>
    <template v-if="material"
      ><p>{{ material.title }} · {{ material.status }}</p>
      <p>任务：{{ material.taskId }}</p>
      <p v-if="material.error" class="form-error">
        {{ material.error.code }}：{{ material.error.message }}
      </p>
      <BaseButton v-if="material.fileId" size="small" @click="original">下载原始文件</BaseButton>
      <article v-for="s in segments" :key="s.id">
        <small>片段 {{ s.ordinal }} / {{ s.extractionMethod }} / 页 {{ s.page ?? '无' }}</small>
        <pre>{{ s.text }}</pre>
      </article>
      <pre v-if="!segments.length">{{ material.textPreview }}</pre>
    </template>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p></BaseModal
  >
</template>
<style scoped>
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
