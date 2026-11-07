<script setup lang="ts">
defineProps<{
  suggestion?: { text: string; needsFactConfirmation: boolean; confirmationHint?: string } | null;
  busy?: boolean;
}>();
defineEmits<{ apply: [] }>();
</script>
<template>
  <section v-if="suggestion" class="ai-result" aria-label="AI 生成内容">
    <div v-if="suggestion.needsFactConfirmation" class="ai-confirmation" role="status">
      <strong>需要补充或核实的信息</strong>
      <p>{{ suggestion.confirmationHint || '请对照原文核实生成内容，并补充能够支持它的事实。' }}</p>
      <small>补充到上方后，再点击「AI 帮助」。</small>
    </div>
    <strong>AI 生成内容</strong>
    <p class="ai-result-text">{{ suggestion.text }}</p>
    <ElButton
      type="primary"
      size="small"
      :disabled="busy || suggestion.needsFactConfirmation"
      @click="$emit('apply')"
      >应用</ElButton
    >
  </section>
</template>

<style scoped>
.ai-result {
  margin-top: 12px;
  padding: 16px;
  border: 1px solid var(--color-accent-border);
  border-radius: 12px;
  background: var(--color-accent-soft);
}
.ai-confirmation {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-left: 3px solid #8c661c;
  border-radius: 4px;
  background: #fff5da;
  color: #513a0f;
  overflow-wrap: anywhere;
}
.ai-confirmation p {
  margin: 4px 0;
  white-space: pre-line;
}
.ai-result-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.8;
}
</style>
