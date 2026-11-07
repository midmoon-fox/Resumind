<script setup lang="ts">
const props = defineProps<{ open: boolean; title: string; wide?: boolean; keepMounted?: boolean }>();
const emit = defineEmits<{ close: [] }>();
</script>
<template>
  <ElDialog
    :model-value="props.open"
    :title="props.title"
    :width="props.wide ? 'min(1040px, calc(100vw - 32px))' : 'min(600px, calc(100vw - 32px))'"
    class="app-dialog"
    :before-close="() => emit('close')"
    :destroy-on-close="!props.keepMounted"
    append-to-body
    ><slot
  /></ElDialog>
</template>
