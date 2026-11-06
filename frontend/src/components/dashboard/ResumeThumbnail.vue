<script setup lang="ts">
import type { ResumeTemplateId } from '../../types/templates';
withDefaults(defineProps<{ variant?: ResumeTemplateId; compact?: boolean }>(), {
  variant: 'simple',
  compact: false,
});
</script>

<template>
  <div
    class="resume-thumbnail"
    :class="[`thumbnail-${variant}`, { 'thumbnail-compact': compact }]"
    aria-hidden="true"
  >
    <div class="thumbnail-paper">
      <div class="thumbnail-heading">
        <div><strong>林同学</strong><span>求职意向</span><span>期待下一段旅程</span></div>
        <i />
      </div>
      <div
        v-for="(section, index) in ['教育背景', '项目经历', '专业技能']"
        :key="section"
        class="thumbnail-section"
      >
        <b>{{ section }}</b>
        <div class="thumbnail-line line-full" />
        <div class="thumbnail-line" />
        <div class="thumbnail-line line-short" />
        <div v-if="index === 1" class="thumbnail-line" />
      </div>
    </div>
  </div>
</template>
