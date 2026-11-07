<script setup lang="ts">
import { ref } from 'vue';
import { ArrowLeft, Sparkles } from '@lucide/vue';
import JobRecommendForm from '../components/jobs/JobRecommendForm.vue';
import JobRecommendResult from '../components/jobs/JobRecommendResult.vue';
import { getJobRecommendations } from '../api/recommend';
import type { RecommendedJob, UserProfile } from '../types';

const loading = ref(false);
const error = ref('');
const recommendations = ref<RecommendedJob[]>([]);
const lastProfile = ref<UserProfile | null>(null);
const emit = defineEmits<{ 'select-job': [job: RecommendedJob] }>();

async function recommend(profile: UserProfile) {
  if (loading.value) return;
  if (!profile.experiences && !profile.skills.length && !profile.personality.length) {
    error.value = '请至少填写一项经历、技能或性格特点。';
    return;
  }
  loading.value = true;
  error.value = '';
  lastProfile.value = profile;
  try {
    recommendations.value = await getJobRecommendations(profile);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '推荐暂时不可用，请稍后重试。';
  } finally {
    loading.value = false;
  }
}
function resetForm() {
  recommendations.value = [];
  error.value = '';
}
</script>

<template>
  <section class="job-match-module" aria-labelledby="job-match-title">
    <header class="job-match-heading">
      <div class="job-match-heading-icon"><Sparkles :size="19" /></div>
      <div>
        <p id="job-match-title">岗位方向 · 本地示例</p>
        <span>用你的资料对照三个岗位方向示例。实际招聘信息可在岗位匹配页查询。</span>
      </div>
    </header>

    <div class="job-match-panel">
      <JobRecommendForm
        v-show="!recommendations.length && !loading"
        :loading="loading"
        @submit="recommend"
      />

      <div v-if="loading" class="recommend-loading" role="status" aria-live="polite">
        <div class="loading-message">
          <span class="loading-orb"><Sparkles :size="18" /></span>
          <div>
            <strong>正在整理岗位方向示例</strong>
            <p>准备可供对照的岗位方向和能力要点。</p>
          </div>
        </div>
        <div class="loading-skeleton-grid">
          <div v-for="item in 3" :key="item" class="loading-skeleton-card">
            <i></i><i></i><i></i><i></i>
          </div>
        </div>
      </div>

      <div v-else-if="recommendations.length" class="recommend-results">
        <div class="results-toolbar">
          <div>
            <span class="results-kicker">{{ recommendations.length }} 个岗位方向示例</span>
            <p>可选择其中一个方向开始制作简历。</p>
          </div>
          <button type="button" class="edit-profile-button" @click="resetForm">
            <ArrowLeft :size="15" /> 修改资料
          </button>
        </div>
        <JobRecommendResult
          :recommendations="recommendations"
          @select="emit('select-job', $event)"
        />
        <p class="profile-recap" v-if="lastProfile">
          本次填写：{{ lastProfile.skills.length ? lastProfile.skills.join(' · ') : '未填写技能'
          }}<span v-if="lastProfile.personality.length">
            · {{ lastProfile.personality.join(' · ') }}</span
          >
        </p>
      </div>

      <p v-if="error" class="recommend-error" role="alert">{{ error }}</p>
    </div>
  </section>
</template>

<style scoped>
.job-match-module {
  display: grid;
  gap: 18px;
}
.job-match-heading {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.job-match-heading-icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--color-accent-border) 22%, transparent);
  border-radius: 14px;
  color: var(--color-accent-text);
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--color-accent) 14%, transparent),
    color-mix(in srgb, var(--color-paper-4) 12%, transparent)
  );
  box-shadow: 0 8px 20px color-mix(in srgb, var(--color-ink) 8%, transparent);
}
.job-match-heading p {
  margin: 2px 0 7px;
  color: var(--color-accent-text);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.16em;
}
.job-match-heading span {
  display: block;
  margin-top: 7px;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.6;
}
.job-match-panel {
  min-width: 0;
  padding: clamp(20px, 3vw, 30px);
  border: 1px solid color-mix(in srgb, var(--color-accent-border) 16%, transparent);
  border-radius: 24px;
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--color-paper) 79%, transparent),
    color-mix(in srgb, var(--color-paper-2) 70%, transparent)
  );
  box-shadow: 0 16px 40px color-mix(in srgb, var(--color-ink) 6%, transparent);
  backdrop-filter: blur(14px);
}
.recommend-results {
  display: grid;
  gap: 18px;
}
.results-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}
.results-kicker {
  color: var(--color-ink);
  font-size: 16px;
  font-weight: 750;
}
.results-toolbar p {
  margin: 5px 0 0;
  color: var(--color-muted);
  font-size: 12px;
}
.edit-profile-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  border: 1px solid color-mix(in srgb, var(--color-accent-border) 20%, transparent);
  border-radius: 10px;
  color: var(--color-accent-text);
  background: color-mix(in srgb, var(--color-paper) 80%, transparent);
  font-size: 12px;
  font-weight: 650;
}
.profile-recap {
  margin: 0;
  color: var(--color-muted);
  font-size: 11px;
}
.recommend-error {
  margin: 14px 0 0;
  color: var(--color-error-ink);
  font-size: 13px;
}
.recommend-loading {
  display: grid;
  gap: 22px;
}
.loading-message {
  display: flex;
  align-items: center;
  gap: 13px;
}
.loading-orb {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 14px;
  color: var(--color-accent-text);
  background: color-mix(in srgb, var(--color-accent) 13%, transparent);
  animation: loading-pulse 1.2s ease-in-out infinite alternate;
}
.loading-message strong {
  color: var(--color-ink);
  font-size: 14px;
}
.loading-message p {
  margin: 5px 0 0;
  color: var(--color-muted);
  font-size: 12px;
}
.loading-skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.loading-skeleton-card {
  display: grid;
  gap: 13px;
  padding: 20px;
  border: 1px solid color-mix(in srgb, var(--color-accent-border) 12%, transparent);
  border-radius: 18px;
  background: color-mix(in srgb, var(--color-paper) 48%, transparent);
}
.loading-skeleton-card i {
  height: 11px;
  border-radius: 999px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--color-accent) 10%, transparent),
    color-mix(in srgb, var(--color-accent) 20%, transparent),
    color-mix(in srgb, var(--color-accent) 10%, transparent)
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.2s linear infinite;
}
.loading-skeleton-card i:first-child {
  width: 52%;
  height: 19px;
}
.loading-skeleton-card i:nth-child(2) {
  width: 100%;
}
.loading-skeleton-card i:nth-child(3) {
  width: 82%;
}
.loading-skeleton-card i:last-child {
  width: 62%;
}
@keyframes skeleton-shimmer {
  to {
    background-position: -200% 0;
  }
}
@keyframes loading-pulse {
  to {
    transform: scale(1.08);
    box-shadow: 0 0 0 8px color-mix(in srgb, var(--color-accent) 6%, transparent);
  }
}
@media (max-width: 760px) {
  .loading-skeleton-grid {
    grid-template-columns: 1fr;
  }
  .loading-skeleton-card:not(:first-child) {
    display: none;
  }
}
@media (max-width: 560px) {
  .job-match-panel {
    padding: 18px;
    border-radius: 19px;
  }
  .results-toolbar {
    align-items: flex-start;
  }
}
@media (prefers-reduced-motion: reduce) {
  .loading-orb,
  .loading-skeleton-card i {
    animation: none;
  }
}
</style>
