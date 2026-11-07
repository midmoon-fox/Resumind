<script setup lang="ts">
import { Trash2 } from '@lucide/vue';
defineProps<{ title: string; anchor: string; expanded: boolean }>();
defineEmits<{ remove: [] }>();
</script>
<template>
  <span class="module-title-row">
    <span class="editor-card-title" :id="anchor">{{ title }}</span>
    <button v-if="expanded" type="button" class="module-title-delete"
      :aria-label="'删除模块' + title" :title="'删除' + title"
      @click.stop="$emit('remove')" @keydown.stop>
      <Trash2 :size="17" />
    </button>
  </span>
</template>
<style scoped>
.module-title-row { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.editor-card-title { flex: 1; min-width: 0; }
.module-title-delete { flex: 0 0 30px; width: 30px; height: 30px; display: inline-flex;
  align-items: center; justify-content: center; border: 0; background: transparent;
  color: #dc2626; border-radius: 6px; cursor: pointer; margin-right: 8px; }
.module-title-delete:hover { background: #fef2f2; }
.module-title-delete:focus-visible { outline: 2px solid #dc2626; outline-offset: 2px; }
</style>
