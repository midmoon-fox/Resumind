<script setup lang="ts">
import { ref } from 'vue';
import { ArrowRight, BriefcaseBusiness, Plus, X } from '@lucide/vue';
import BaseButton from '../common/BaseButton.vue';
import type { UserProfile } from '../../types';

defineProps<{ loading?: boolean }>();
const emit = defineEmits<{ submit: [profile: UserProfile] }>();
const experiences = ref('');
const skillInput = ref('');
const skills = ref<string[]>([]);
const personality = ref<string[]>([]);
const traits = ['逻辑严密', '外向沟通', '执行力强', '创意发散', '共情倾听', '抗压适应'];

function addSkill(raw = skillInput.value) {
  const value = raw
    .trim()
    .replace(/[,，]+$/, '')
    .trim();
  if (
    value &&
    !skills.value.some((item) => item.toLocaleLowerCase() === value.toLocaleLowerCase())
  ) {
    skills.value.push(value);
  }
  skillInput.value = '';
}
function handleSkillInput(event: Event) {
  const input = event.target as HTMLInputElement;
  const parts = input.value.split(/[,，]/);
  if (parts.length > 1) {
    parts.slice(0, -1).forEach((part) => addSkill(part));
    skillInput.value = parts.at(-1) ?? '';
  } else skillInput.value = input.value;
}
function toggleTrait(trait: string) {
  personality.value = personality.value.includes(trait)
    ? personality.value.filter((item) => item !== trait)
    : [...personality.value, trait];
}
function removeSkill(skill: string) {
  skills.value = skills.value.filter((item) => item !== skill);
}
function submit() {
  addSkill();
  emit('submit', {
    experiences: experiences.value.trim(),
    skills: [...skills.value],
    personality: [...personality.value],
  });
}
</script>

<template>
  <form class="recommend-form" @submit.prevent="submit">
    <label class="recommend-field">
      <span>实习 / 项目经历 <small>（选填）</small></span>
      <textarea
        v-model="experiences"
        rows="5"
        maxlength="3000"
        placeholder="写下你做过的实习、项目、负责内容或取得的结果……"
        :disabled="loading"
      />
      <small class="recommend-hint">记录可用于后续对照岗位要求的真实经历。</small>
    </label>

    <div class="recommend-field">
      <label for="recommend-skills">技能关键词</label>
      <div class="skill-entry">
        <input
          id="recommend-skills"
          :value="skillInput"
          maxlength="40"
          placeholder="例如：数据分析、Figma、用户访谈"
          :disabled="loading"
          @input="handleSkillInput"
          @keydown.enter.prevent="addSkill()"
          @keydown="
            $event.key === ',' || $event.key === '，'
              ? ($event.preventDefault(), addSkill())
              : undefined
          "
        />
        <button
          class="skill-add"
          type="button"
          :disabled="loading"
          aria-label="添加技能"
          @click="addSkill()"
        >
          <Plus :size="17" /> 添加
        </button>
      </div>
      <div v-if="skills.length" class="recommend-tags" aria-label="已添加技能">
        <span v-for="skill in skills" :key="skill" class="recommend-tag skill-tag">
          {{ skill }}
          <button type="button" :aria-label="`移除技能 ${skill}`" @click="removeSkill(skill)">
            <X :size="13" />
          </button>
        </span>
      </div>
      <small class="recommend-hint">按回车或输入逗号即可添加多个技能。</small>
    </div>

    <fieldset class="recommend-field trait-field">
      <legend>性格特点 <small>（可多选）</small></legend>
      <div class="recommend-tags">
        <button
          v-for="trait in traits"
          :key="trait"
          class="recommend-tag trait-tag"
          :class="{ selected: personality.includes(trait) }"
          type="button"
          :aria-pressed="personality.includes(trait)"
          :disabled="loading"
          @click="toggleTrait(trait)"
        >
          {{ trait }}
        </button>
      </div>
    </fieldset>

    <div class="recommend-form-footer">
      <p><BriefcaseBusiness :size="17" /> 填写资料后查看本地岗位方向示例</p>
      <BaseButton type="submit" :loading="loading" :disabled="loading">
        查看 JD 方向示例 <ArrowRight :size="17" />
      </BaseButton>
    </div>
  </form>
</template>

<style scoped>
.recommend-form {
  display: grid;
  gap: 24px;
}
.recommend-field {
  display: grid;
  gap: 9px;
  min-width: 0;
  padding: 0;
  border: 0;
}
.recommend-field > span,
.recommend-field > label,
.recommend-field > legend {
  color: var(--color-ink);
  font-size: 14px;
  font-weight: 700;
}
.recommend-field small {
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 400;
}
.recommend-field textarea,
.skill-entry input {
  width: 100%;
  border: 1px solid var(--color-rule);
  border-radius: 14px;
  padding: 13px 15px;
  color: var(--color-ink);
  background: color-mix(in srgb, var(--color-paper) 74%, transparent);
  outline: none;
  transition:
    border-color 0.18s,
    box-shadow 0.18s;
}
.recommend-field textarea {
  min-height: 126px;
  resize: vertical;
  line-height: 1.65;
}
.recommend-field textarea:focus,
.skill-entry input:focus {
  border-color: var(--color-focus);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-accent-border) 14%, transparent);
}
.recommend-hint {
  color: var(--color-muted);
  font-size: 12px;
}
.skill-entry {
  display: flex;
  gap: 10px;
}
.skill-add {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0 13px;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
  color: var(--color-accent-text);
  background: var(--color-paper);
  font-weight: 650;
}
.recommend-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}
.recommend-tag {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  border: 1px solid color-mix(in srgb, var(--color-accent-border) 18%, transparent);
  border-radius: 999px;
  color: var(--color-ink-2);
  background: color-mix(in srgb, var(--color-paper) 65%, transparent);
  font-size: 13px;
}
.recommend-tag button {
  display: inline-flex;
  padding: 0;
  border: 0;
  color: inherit;
  background: transparent;
}
.trait-tag.selected {
  border-color: color-mix(in srgb, var(--color-accent) 46%, transparent);
  color: var(--color-accent-text);
  background: color-mix(in srgb, var(--color-accent) 12%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--color-accent) 10%, transparent);
}
.trait-tag:disabled,
.skill-add:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.recommend-form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-top: 5px;
}
.recommend-form-footer p {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
}
.recommend-form-footer p :deep(svg) {
  color: var(--color-accent-text);
}
@media (max-width: 640px) {
  .recommend-form-footer {
    align-items: stretch;
    flex-direction: column;
  }
  .recommend-form-footer :deep(.base-button) {
    justify-content: center;
  }
}
</style>
