<script setup lang="ts">
import type { Profile } from '../../types/app';
import { toProfile } from '../../services/mapping';
import BaseButton from '../common/BaseButton.vue';
import { computed, ref, watch } from 'vue';
const props = defineProps<{ profile: Profile }>();
const ageInput = ref(props.profile.age == null ? '' : String(props.profile.age));
watch(() => props.profile.age, (age) => { ageInput.value = age == null ? '' : String(age); });
const ageError = computed(() => ageInput.value !== '' &&
  (!/^\d+$/.test(ageInput.value) || Number(ageInput.value) > 100)
  ? '年龄请输入 0–100 之间的整数' : '');
function updateAge(value: string) {
  ageInput.value = value;
  if (!ageError.value) props.profile.age = value === '' ? null : Number(value);
}
function add() {
  props.profile.education = toProfile(props.profile, '').education;
  props.profile.education.push({
    id: crypto.randomUUID(),
    school: '',
    major: '',
    degree: '本科',
    startDate: null,
    endDate: null,
    isCurrent: false,
  });
}
</script>
<template>
  <div
    v-for="(education, index) in (profile.education ?? []).slice(1)"
    :key="education.id"
    class="experience-card"
  >
    <h3>其他教育经历 {{ index + 1 }}</h3>
    <label class="field">学校<ElInput v-model="education.school" aria-label="学校" /></label
    ><label class="field">专业<ElInput v-model="education.major" aria-label="专业" /></label
    ><label class="field">学历<ElInput v-model="education.degree" aria-label="学历" /></label>
    <div class="form-grid">
      <label class="field"
        >开始月份<ElDatePicker
          v-model="education.startDate"
          type="month"
          format="YYYY-MM"
          value-format="YYYY-MM"
          aria-label="开始月份" /></label
      ><label class="field"
        >结束月份<ElDatePicker
          v-model="education.endDate"
          :disabled="education.isCurrent"
          type="month"
          format="YYYY-MM"
          value-format="YYYY-MM"
          aria-label="结束月份"
      /></label>
    </div>
    <ElCheckbox class="check-label" v-model="education.isCurrent">在读</ElCheckbox
    ><button class="text-link danger-text" @click="profile.education!.splice(index + 1, 1)">
      删除这段教育经历
    </button>
  </div>
  <BaseButton size="small" variant="secondary" :disabled="!profile.school.trim()" @click="add"
    >新增其他教育经历</BaseButton
  ><label class="field"
    >年龄（选填）<ElInput
      :model-value="ageInput"
      @update:model-value="updateAge"
      inputmode="numeric"
      style="width: 120px; max-width: 100%"
      placeholder="0–100"
      :aria-invalid="!!ageError"
      aria-label="年龄（选填）"
  /><span v-if="ageError" class="form-error" role="alert">{{ ageError }}</span></label>
</template>
