<script setup lang="ts">
import AiResult from './AiResult.vue';
import RichTextEditor from './RichTextEditor.vue';
const props = defineProps<{
  modelValue: string;
  label: string;
  busy?: boolean;
  notice?: string;
  suggestion?: { text: string; needsFactConfirmation: boolean; confirmationHint?: string } | null;
}>();
const emit = defineEmits<{ 'update:modelValue': [value: string]; 'ai-help': []; apply: [] }>();
</script>
<template>
  <div class="ai-text-field">
    <RichTextEditor
      :model-value="modelValue"
      :label="label"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <div class="ai-field-bar">
      <span v-if="notice" class="ai-notice" role="status">{{ notice }}</span>
      <ElButton type="primary" class="ai-help-button" :loading="busy" @click="emit('ai-help')"
        >AI 帮助</ElButton
      >
    </div>
    <AiResult :suggestion="suggestion" :busy="busy" @apply="emit('apply')" />
  </div>
</template>
<style scoped>
.ai-text-field :deep(.rich-editor) {
  min-height: 220px;
}
.ai-text-field :deep(.rich-editor .ProseMirror) {
  min-height: 180px;
  max-height: 400px;
  overflow-y: auto;
}
.ai-field-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 6px;
}
.ai-help-button {
  height: 40px;
  padding: 0 22px;
  font-size: 15px;
  border: none;
  background: linear-gradient(135deg, #4f6ef7, #7c3aed);
}
.ai-help-button:hover,
.ai-help-button:focus {
  background: linear-gradient(135deg, #5d7bf8, #8b4ff0);
}
.ai-notice {
  font-size: 12px;
  color: var(--color-muted);
  margin-right: auto;
}
</style>
