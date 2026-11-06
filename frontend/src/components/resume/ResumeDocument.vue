<script setup lang="ts">
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import type { ResumeDocument } from '../../types/app';
import { authenticatedFetch } from '../../services/client';
import { parsePreviewMessage, type EditTarget } from '../../services/editorTargets';
const props = withDefaults(defineProps<{ document: ResumeDocument; editable?: boolean }>(), {
  editable: false,
});
const emit = defineEmits<{ 'select-target': [target: EditTarget] }>();
const surface = ref<HTMLElement>();
const iframeEl = ref<HTMLIFrameElement>();
const channel = ref('');
// Reserve room inside the iframe for its vertical scrollbar. A 794px frame
// leaves less than A4 width once that scrollbar appears.
const frameWidth = 826;
const scale = ref(1);
const viewportHeight = ref(600);
const previewHtml = computed(() =>
  html.value.replace(
    '</head>',
    `<style>
html { overflow-x: hidden !important; }
body { margin: 0 !important; padding: 0 !important; width: 794px; }
.sheet { width: 794px !important; margin: 0 !important; box-shadow: none !important; }
</style></head>`,
  ),
);
let observer: ResizeObserver;
onMounted(() => {
  observer = new ResizeObserver(() => {
    scale.value = Math.min(1, (surface.value?.clientWidth || frameWidth) / frameWidth);
    viewportHeight.value = surface.value?.clientHeight || 600;
  });
  if (surface.value) observer.observe(surface.value);
});
onBeforeUnmount(() => observer?.disconnect());
const previewError = ref('');
const html = ref(''),
  loading = ref(false);
let sequence = 0;
const key = computed(
  () =>
    `${props.document.id}:${props.document.revision}:${props.document.versionId ?? ''}:${props.editable}`,
);
watch(
  key,
  async () => {
    const current = ++sequence;
    html.value = '';
    previewError.value = '';
    channel.value = '';
    if (props.document.versionId) return;
    loading.value = true;
    const ch = crypto.randomUUID();
    try {
      const response = await authenticatedFetch(
        `/api/resumes/${props.document.id}/preview${props.editable ? `?edit=1&channel=${ch}` : ''}`,
      );
      // 模板无内容时静默，不渲染预览
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.error?.message || `简历预览加载失败（${response.status}），请重试`);
      }
      const value = await response.text();
      if (current === sequence) {
        html.value = value;
        channel.value = ch;
      }
    } catch (error) {
      if (current === sequence)
        previewError.value = error instanceof Error ? error.message : '简历预览暂时无法加载';
    } finally {
      if (current === sequence) loading.value = false;
    }
  },
  { immediate: true },
);
function handleMessage(event: MessageEvent) {
  if (!props.editable) return;
  const target = parsePreviewMessage(event.data, {
    channel: channel.value,
    resumeId: props.document.id,
    revision: props.document.revision,
  });
  if (!target) return;
  if (event.source !== iframeEl.value?.contentWindow) return;
  emit('select-target', target);
}
onMounted(() => window.addEventListener('message', handleMessage));
onBeforeUnmount(() => window.removeEventListener('message', handleMessage));
</script>
<template>
  <div ref="surface" class="server-resume-preview" :aria-busy="loading">
    <template v-if="document.versionId"
      ><p>历史内容快照（非导出版式预览）</p>
      <pre>{{ document.backend?.document }}</pre>
    </template>
    <p v-else-if="loading" role="status">正在加载后端模板预览…</p>
    <p v-else-if="previewError" class="form-error" role="alert">{{ previewError }}</p>
    <iframe
      v-else-if="html"
      ref="iframeEl"
      :srcdoc="previewHtml"
      :style="{
        width: frameWidth + 'px',
        height: Math.ceil(viewportHeight / scale) + 'px',
        transform: `scale(${scale})`,
        transformOrigin: 'top left',
      }"
      :sandbox="editable && !document.versionId ? 'allow-scripts' : ''"
      title="后端简历 A4 预览"
    />
  </div>
</template>
<style scoped>
.server-resume-preview {
  width: 100%;
  min-width: 0;
  background: white;
  overflow: hidden;
  height: 100%;
}
iframe {
  width: 100%;
  min-height: 0;
  height: 100%;
  border: 0;
  background: white;
}
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  padding: 16px;
}
</style>
