<script setup lang="ts">
const props = defineProps<{ open: boolean; title: string; wide?: boolean }>();
const emit = defineEmits<{ close: [] }>();
</script>
<template>
  <ElDialog
    :model-value="props.open"
    :title="props.title"
    :width="props.wide ? 'min(1040px, calc(100vw - 32px))' : 'min(600px, calc(100vw - 32px))'"
    class="app-dialog"
    :before-close="() => emit('close')"
    destroy-on-close
    append-to-body
    ><slot
  /></ElDialog>
</template>
