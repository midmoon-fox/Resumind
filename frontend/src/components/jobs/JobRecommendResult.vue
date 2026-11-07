<script setup lang="ts">
import { ArrowRight, CircleCheck, TrendingUp } from '@lucide/vue';
import BaseButton from '../common/BaseButton.vue';
import type { RecommendedJob } from '../../types';

defineProps<{ recommendations: RecommendedJob[] }>();
const emit = defineEmits<{ select: [job: RecommendedJob] }>();
</script>

<template>
  <div class="recommend-result-grid">
    <article
      v-for="(job, index) in recommendations"
      :key="job.id"
      class="recommend-result-card"
      :style="{ '--card-index': index }"
    >
      <div class="result-card-header">
        <div>
          <span class="result-rank">推荐方向 0{{ index + 1 }}</span>
          <h3>{{ job.title }}</h3>
        </div>
      </div>

      <p class="result-reason"><TrendingUp :size="16" />{{ job.reason }}</p>
      <div class="result-section">
        <h4><CircleCheck :size="15" /> 可关注的能力</h4>
        <div class="recommend-tags">
          <span v-for="skill in job.focus" :key="skill" class="result-tag strength-tag">{{
            skill
          }}</span>
        </div>
      </div>
      <div class="result-section">
        <h4 class="gap-heading">建议补充</h4>
        <div class="recommend-tags">
          <span v-for="gap in job.gaps" :key="gap" class="result-tag gap-tag">{{ gap }}</span>
        </div>
      </div>

      <div class="result-card-footer">
        <span>方向建议仅供求职规划参考</span>
        <BaseButton size="small" @click="emit('select', job)"
          >去生成此岗位的简历 <ArrowRight :size="15"
        /></BaseButton>
      </div>
    </article>
  </div>
</template>

<style scoped>
.recommend-result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 16px;
}
.recommend-result-card {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 17px;
  padding: 22px;
  border: 1px solid color-mix(in srgb, var(--color-accent-border) 16%, transparent);
  border-radius: 20px;
  background: linear-gradient(
    150deg,
    color-mix(in srgb, var(--color-paper) 86%, transparent),
    color-mix(in srgb, var(--color-paper-2) 72%, transparent)
  );
  box-shadow: 0 12px 32px color-mix(in srgb, var(--color-ink) 6%, transparent);
  animation: result-appear 0.4s both;
  animation-delay: calc(var(--card-index) * 90ms);
}
.result-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.result-rank {
  color: var(--color-accent-text);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.08em;
}
.result-card-header h3 {
  margin: 8px 0 0;
  color: var(--color-ink);
  font-size: 21px;
  letter-spacing: -0.03em;
}
.result-reason {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0;
  color: var(--color-ink-2);
  font-size: 13px;
  line-height: 1.65;
}
.result-reason :deep(svg) {
  flex: 0 0 auto;
  margin-top: 2px;
  color: var(--color-accent-text);
}
.result-section {
  display: grid;
  gap: 9px;
}
.result-section h4 {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: var(--color-success-ink);
  font-size: 12px;
}
.result-section h4 :deep(svg) {
  color: var(--color-success-ink);
}
.result-section .gap-heading {
  color: var(--color-warning);
}
.recommend-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.result-tag {
  display: inline-flex;
  padding: 5px 9px;
  border: 1px solid transparent;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.4;
}
.strength-tag {
  border-color: color-mix(in srgb, var(--color-success) 16%, transparent);
  color: var(--color-success-ink);
  background: color-mix(in srgb, var(--color-success) 10%, transparent);
}
.gap-tag {
  border-color: color-mix(in srgb, var(--color-warning) 18%, transparent);
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 14%, transparent);
}
.result-card-footer {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  margin-top: auto;
  padding-top: 4px;
}
.result-card-footer > span {
  color: var(--color-muted);
  font-size: 11px;
}
@keyframes result-appear {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@media (max-width: 680px) {
  .recommend-result-card {
    padding: 19px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .recommend-result-card {
    animation: none;
  }
}
</style>
