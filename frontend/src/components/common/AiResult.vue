<script setup lang="ts">
defineProps<{
  suggestion?: { text: string; needsFactConfirmation: boolean } | null;
  busy?: boolean;
}>();
defineEmits<{ apply: [] }>();
</script>
<template>
  <section v-if="suggestion" class="ai-result" aria-label="AI 生成内容">
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
  border: 1px solid #A7CEFC;
  border-radius: 12px;
  background: #FFFFFF;
}
.ai-result-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.8;
}
</style>
