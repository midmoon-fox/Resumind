<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  ArrowDownWideNarrow,
  ArrowRight,
  CalendarDays,
  FileText,
  Plus,
  SearchX,
  Sparkles,
  X,
} from '@lucide/vue';
import BaseButton from '../components/common/BaseButton.vue';
import HeroIllustration from '../components/dashboard/HeroIllustration.vue';
import FeatureCard from '../components/dashboard/FeatureCard.vue';
import ResumeCard from '../components/dashboard/ResumeCard.vue';
import { useDashboard } from '../composables/useDashboard';
import { useAppStore } from '../composables/useAppStore';
import type { FeatureKey, ResumeSummary } from '../types/dashboard';
const router = useRouter();
const { state } = useAppStore();
const { resumes, search, sortOrder, filteredResumes } = useDashboard();
const today = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long',
  timeZone: 'Asia/Shanghai',
}).format(new Date());
const tasks = ref([
  { id: 'profile', title: '确定你的求职方向', subtitle: '每一段旅程，始于一个目标', done: true },
  {
    id: 'resume',
    title: '准备一份岗位定制简历',
    subtitle: '结合目标 JD，整理真实经历',
    done: false,
  },
  { id: 'interview', title: '为下一场面试做准备', subtitle: '多一分准备，多一分从容', done: false },
]);
tasks.value.forEach((task, index) => {
  task.done = state.goals[index] ?? task.done;
});
watch(
  tasks,
  () => {
    state.goals = tasks.value.map((task) => task.done);
  },
  { deep: true },
);
const completedTasks = computed(() => tasks.value.filter((t) => t.done).length);
function openCreate() {
  void router.push('/create');
}
function selectFeature(feature: FeatureKey) {
  void router.push({ generator: '/create', jobs: '/jobs', interview: '/interview' }[feature]);
}
function openResume(resume: ResumeSummary) {
  void router.push('/resumes/' + resume.id + '/edit');
}
function showAll() {
  search.value = '';
  void router.push('/resumes');
}
</script>

<template>
  <div class="dashboard">
    <section class="welcome-row" aria-labelledby="welcome-title">
      <div>
        <h1 class="wrap-heading" id="welcome-title">
          你好，{{ state.account.nickname }}
          <Sparkles class="welcome-symbol" :size="20" aria-hidden="true" />
        </h1>
        
      </div>
      <div class="welcome-actions">
        <span class="today"><CalendarDays :size="16" />{{ today }}</span
        ><BaseButton size="small" @click="openCreate"><Plus :size="17" />新建简历</BaseButton>
      </div>
    </section>

    <section class="hero-banner" aria-labelledby="hero-title">
      <!-- <RibbonBackdrop /> -->
      <div class="hero-content">
        <h2 class="wrap-heading" id="hero-title">简立得，一体化定制岗位简历</h2>
        <p>结合目标岗位 JD，筛选并组织相关经历，生成可编辑的定制简历</p>
        <div class="hero-buttons">
          <BaseButton @click="openCreate"
            ><Sparkles :size="17" />开始制作定制简历<ArrowRight :size="17" /></BaseButton
          >
        </div>
        
      </div>
      <HeroIllustration />
    </section>

    <section class="quick-start" aria-labelledby="quick-title">
      <div class="section-heading">
        <h2 class="wrap-heading" id="quick-title">
          你的AI求职助手<span>我们不只可以帮你制作简历简历</span>
        </h2>
        <span class="subtle-label">以真实经历为基础</span>
      </div>
      <div class="feature-grid">
        <FeatureCard
          feature="generator"
          eyebrow="TAILORED RESUME"
          title="一站式迅速定制简历"
          description="以真实经历为基础，结合目标岗位 JD 筛选和组织内容，生成可编辑的专属简历。"
          action="开始定制简历"
          @select="selectFeature"
        />
        <FeatureCard
          feature="jobs"
          eyebrow="DISCOVER"
          title="岗位推荐"
          description="浏览示例岗位，查看技能关键词重合度，为下一份定制简历找到方向。"
          action="按岗位探索机会"
          @select="selectFeature"
        />
        <FeatureCard
          feature="interview"
          eyebrow="PREPARE"
          title="面试准备"
          description="围绕你的简历和求职方向，准备自我介绍与常见问题，练习真实表达。"
          action="了解模拟面试"
          @select="selectFeature"
        />
      </div>
    </section>

    <div class="dashboard-lower">
      <section id="recent-resumes" class="recent-section" aria-labelledby="recent-title">
        <div class="section-heading recent-heading">
          <div>
            <h2 class="wrap-heading" id="recent-title">
              最近简历 <span class="count-badge">{{ resumes.length }}</span>
            </h2>
   
          </div>
          <button type="button" class="text-link" @click="showAll">
            查看全部 <ArrowRight :size="15" />
          </button>
        </div>
        <div class="resume-toolbar">
          <span
            ><FileText :size="15" />{{ search ? '搜索结果' : '我的全部简历'
            }}<small>{{ filteredResumes.length }} 份</small></span
          ><label class="sort-control"
            ><ArrowDownWideNarrow :size="14" /><ElSelect
              v-model="sortOrder"
              aria-label="简历排序方式"
              ><ElOption value="updated" :label="'最近更新'" />
              <ElOption value="name" :label="'按名称排序'" /></ElSelect
          ></label>
        </div>
        <div v-if="filteredResumes.length" class="resume-grid">
          <ResumeCard
            v-for="resume in filteredResumes"
            :key="resume.id"
            :resume="resume"
            @preview="openResume"
          />
          <button type="button" class="new-resume-card" @click="openCreate">
            <span><Plus :size="23" /></span><strong>下一份精彩，从这里开始</strong
            ><small>新建一份简历 <ArrowRight :size="13" /></small>
          </button>
        </div>
        <div v-else class="empty-state">
          <SearchX :size="30" />
          <h3 class="wrap-heading">没有找到这份简历</h3>
          <p>换个关键词试试，或清空搜索查看全部。</p>
          <BaseButton variant="secondary" size="small" @click="search = ''"
            >清空搜索 <X :size="14"
          /></BaseButton>
        </div>
        <div class="resume-summary">
          <!-- <span><CheckCheck :size="15" />{{ readyCount }} 份简历基础资料完整</span> -->
        </div>
      </section>

      <aside class="journey-panel" aria-labelledby="journey-title">
        <div class="journey-header">
          <span class="journey-icon"><Sparkles :size="18" /></span>
          <h2 class="wrap-heading" id="journey-title">我的求职小目标</h2>
          <span>{{ completedTasks }}/{{ tasks.length }}</span>
        </div>

        <div
          class="journey-progress"
          role="progressbar"
          aria-label="求职目标完成进度"
          :aria-valuenow="completedTasks"
          :aria-valuemin="0"
          :aria-valuemax="tasks.length"
        >
          <span :style="{ width: (completedTasks / tasks.length) * 100 + '%' }" />
        </div>
        <div class="journey-task-list">
          <ElCheckbox
            v-for="task in tasks"
            :key="task.id"
            class="journey-task"
            :class="{ 'task-done': task.done }"
            v-model="task.done"
            ><span
              ><strong>{{ task.title }}</strong
              ><small>{{ task.subtitle }}</small></span
            ></ElCheckbox
          >
        </div>
        <div class="journey-divider" />
        
      </aside>
    </div>

  </div>
</template>

<style scoped>
/* Hallmark · shape: app screen · genre: modern-minimal · theme: brand · redesign: full · v2.0.0 */
/* Hallmark · pre-emit critique: P4 H5 E4 S4 R5 V3 · weakest: V, kept shared workspace shell */
.wrap-heading {
  overflow-wrap: break-word;
  min-width: 0;
  text-wrap: balance;
}
</style>
