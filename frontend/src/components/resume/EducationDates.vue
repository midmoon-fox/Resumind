<script setup lang="ts">
import { computed } from 'vue';
import { dates, periodText } from '../../services/mapping';
const props = defineProps<{ modelValue: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const value = computed(() => {
  try { return dates(props.modelValue); }
  catch { return { startDate: null, endDate: null, isCurrent: false }; }
});
function start(value_: string | null) {
  if (!value_) { emit('update:modelValue', ''); return; }
  const current = value.value;
  emit('update:modelValue', periodText({ ...current, startDate: value_,
    endDate: current.endDate && current.endDate >= value_ ? current.endDate : null }));
}
function end(value_: string | null) {
  emit('update:modelValue', periodText({ ...value.value, endDate: value_ || null }));
}
function current(checked: boolean | string | number) {
  emit('update:modelValue', periodText({ ...value.value, isCurrent: checked === true,
    endDate: null }));
}
function beforeStart(date: Date) {
  const month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
  return !!value.value.startDate && month < value.value.startDate;
}
</script>
<template>
  <div class="education-dates">
    <ElDatePicker :model-value="value.startDate" type="month" format="YYYY-MM"
      value-format="YYYY-MM" placeholder="开始月份" aria-label="教育开始月份"
      @update:model-value="start" />
    <span aria-hidden="true">至</span>
    <ElDatePicker :model-value="value.endDate" type="month" format="YYYY-MM"
      value-format="YYYY-MM" :placeholder="value.isCurrent ? '至今' : '结束月份'"
      :disabled="!value.startDate || value.isCurrent" :disabled-date="beforeStart"
      aria-label="教育结束月份" @update:model-value="end" />
    <ElCheckbox :model-value="value.isCurrent" :disabled="!value.startDate" @change="current">在读</ElCheckbox>
  </div>
</template>
<style scoped>
.education-dates { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.education-dates :deep(.el-date-editor.el-input) { width: 160px; max-width: 100%; flex: 0 1 160px; }
</style>
