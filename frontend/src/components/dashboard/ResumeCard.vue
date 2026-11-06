<script setup lang="ts">
import { ArrowUpRight, Clock3, Eye } from '@lucide/vue';
import type { ResumeSummary } from '../../types/dashboard';
import ResumeThumbnail from './ResumeThumbnail.vue';
defineProps<{ resume: ResumeSummary }>();
const emit = defineEmits<{ preview: [resume: ResumeSummary] }>();
function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    timeZone: 'Asia/Shanghai',
  }).format(new Date(value));
}
</script>

<template>
  <article class="resume-card">
    <button
      type="button"
      class="resume-preview-button"
      :aria-label="`预览${resume.title}`"
      @click="emit('preview', resume)"
    >
      <ResumeThumbnail :variant="resume.template" /><span class="resume-preview-overlay"
        ><Eye :size="19" />查看预览</span
      >
      <span class="resume-status" :class="`status-${resume.status}`">{{
        resume.status === 'ready' ? '资料完整' : '草稿'
      }}</span>
    </button>
    <div class="resume-card-content">
      <h3 class="wrap-heading" :title="resume.title">{{ resume.title }}</h3>
      <div class="resume-card-meta">
        <span><Clock3 :size="13" />{{ formatDate(resume.updatedAt) }} 更新</span
        ><button
          type="button"
          class="resume-open-button"
          :aria-label="`查看${resume.title}详情`"
          @click="emit('preview', resume)"
        >
          <ArrowUpRight :size="17" />
        </button>
      </div>
    </div>
  </article>
</template>
