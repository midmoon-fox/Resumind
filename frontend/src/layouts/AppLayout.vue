<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ArrowRight, Check, Sparkles } from '@lucide/vue';
import AppSidebar from '../components/layout/AppSidebar.vue';
import AppHeader from '../components/layout/AppHeader.vue';
import BaseModal from '../components/common/BaseModal.vue';
import BaseButton from '../components/common/BaseButton.vue';
import DemoNotice from '../components/common/DemoNotice.vue';

const mobileMenuOpen = ref(false);
const helpOpen = ref(false);
const route = useRoute();
watch(
  () => route.fullPath,
  () => {
    mobileMenuOpen.value = false;
  },
);
let navigationTrigger: HTMLElement | null = null;
let pageOverflow = '';
const desktopQuery = window.matchMedia('(min-width: 961px)');

watch(mobileMenuOpen, async (open) => {
  if (open) {
    navigationTrigger = document.activeElement as HTMLElement | null;
    pageOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    await nextTick();
    document.querySelector<HTMLElement>('.mobile-close')?.focus();
  } else {
    document.body.style.overflow = pageOverflow;
    await nextTick();
    navigationTrigger?.focus();
  }
});

function handleNavigationKeys(event: KeyboardEvent) {
  if (!mobileMenuOpen.value) return;
  if (event.key === 'Escape') {
    event.preventDefault();
    mobileMenuOpen.value = false;
  }
  if (event.key !== 'Tab') return;
  const items = Array.from(
    document.querySelectorAll<HTMLElement>('#main-sidebar a[href], #main-sidebar button'),
  ).filter((item) => item.getClientRects().length > 0);
  const first = items[0];
  const last = items[items.length - 1];
  if (!first || !last) return;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function handleDesktop(event: MediaQueryListEvent) {
  if (event.matches) mobileMenuOpen.value = false;
}

onMounted(() => {
  document.addEventListener('keydown', handleNavigationKeys);
  desktopQuery.addEventListener('change', handleDesktop);
});
onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleNavigationKeys);
  desktopQuery.removeEventListener('change', handleDesktop);
  if (mobileMenuOpen.value) document.body.style.overflow = pageOverflow;
});
</script>

<template>
  <div v-if="route.meta.authPage"><slot /></div>
  <div v-else-if="route.meta.creationSession" class="creation-shell">
    <a href="#main-content" class="skip-link">跳到制作简历</a>
    <main id="main-content" class="creation-main" tabindex="-1"><slot /></main>
  </div>
  <div v-else class="app-shell">
    <a href="#main-content" class="skip-link">跳到页面内容</a>
    <AppSidebar :open="mobileMenuOpen" @close="mobileMenuOpen = false" @help="helpOpen = true" />
    <div class="app-main" :inert="mobileMenuOpen || undefined">
      <AppHeader
        :menu-open="mobileMenuOpen"
        @menu="mobileMenuOpen = true"
        @help="helpOpen = true"
      />
      <DemoNotice />
      <main id="main-content" tabindex="-1"><slot /></main>
    </div>
    <BaseModal :open="helpOpen" title="从这里，开始你的求职旅程" @close="helpOpen = false">
      <div class="help-intro">
        <span class="feature-icon"><Sparkles :size="23" /></span>
        <p>先把经历整理好，再让机会找到你。</p>
      </div>
      <ol class="help-list">
        <li><Check :size="18" />从制作向导填写资料、核对经历并选择模板。</li>
        <li><Check :size="18" />在编辑器调整内容和样式，保存版本或导出。</li>
        <li><Check :size="18" />查询真实海外岗位，确认 JD，生成面试准备资料。</li>
      </ol>
      <p class="demo-notice">业务功能通过 JWT 登录后调用后端接口。收藏和提醒偏好仅保存到本机。</p>
      <BaseButton class="full-width" @click="helpOpen = false"
        >开始探索 <ArrowRight :size="17"
      /></BaseButton>
    </BaseModal>
  </div>
</template>

<style scoped>
/* Hallmark · shape: app screen · genre: modern-minimal · theme: brand · redesign: full · v2.0.0 */
/* Hallmark · pre-emit critique: P4 H5 E4 S4 R5 V3 · weakest: V, kept shared workspace shell */
.app-main {
  min-width: 0;
}
</style>

<style scoped>
.creation-shell {
  min-height: 100dvh;
  width: 100%;
  background: var(--color-paper-2);
}
.creation-main {
  width: 100%;
  min-width: 0;
  margin: 0;
}
</style>
