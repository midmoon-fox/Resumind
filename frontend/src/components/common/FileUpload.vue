<script setup lang="ts">
import { ref } from 'vue';
import type { UploadFile, UploadInstance } from 'element-plus';
withDefaults(
  defineProps<{ accept?: string; multiple?: boolean; disabled?: boolean; drag?: boolean }>(),
  {
    multiple: false,
    drag: false,
    disabled: false,
  },
);
const emit = defineEmits<{ select: [files: File[]] }>();
const uploader = ref<UploadInstance>();
let pending: File[] = [],
  scheduled = false;
function changed(file: UploadFile) {
  if (!file.raw) return;
  pending.push(file.raw);
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => {
    const files = pending;
    pending = [];
    scheduled = false;
    uploader.value?.clearFiles();
    emit('select', files);
  });
}
</script>
<template>
  <ElUpload
    ref="uploader"
    :accept="accept"
    :drag="drag"
    :multiple="multiple"
    :disabled="disabled"
    :auto-upload="false"
    :show-file-list="false"
    :on-change="changed"
    class="file-upload"
  >
    <slot><ElButton :disabled="disabled" type="primary" plain>选择文件</ElButton></slot>
  </ElUpload>
</template>
<style scoped>
.file-upload {
  min-width: 0;
}
.file-upload :deep(.el-upload) {
  max-width: 100%;
}
.file-upload.upload-zone :deep(.el-upload) {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  padding: 8px;
}
</style>
