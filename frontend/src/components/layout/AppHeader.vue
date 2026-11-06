<script setup lang="ts">
import { Bell, ChevronDown, CircleHelp, Menu, Search } from '@lucide/vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '../../composables/useAppStore';
import { useDashboard } from '../../composables/useDashboard';
import { useToast } from '../../composables/useToast';
defineProps<{ menuOpen: boolean }>();
const emit = defineEmits<{ menu: []; help: [] }>();
const { search } = useDashboard();
const { state } = useAppStore();
const route = useRoute(),
  router = useRouter();
const { notify } = useToast();
</script>

<template>
  <header class="topbar">
    <div class="topbar-leading">
      <button
        type="button"
        class="icon-button mobile-menu"
        aria-label="打开导航菜单"
        aria-controls="main-sidebar"
        :aria-expanded="menuOpen"
        @click="emit('menu')"
      >
        <Menu :size="22" />
      </button>
      <span class="breadcrumb"
        ><span class="breadcrumb-root">我的空间</span><span class="breadcrumb-separator">/</span
        ><strong>{{ route.meta.title }}</strong></span
      >
    </div>
    <div class="topbar-actions">
      <label class="search-input"
        ><Search :size="17" /><ElInput
          v-model="search"
          aria-label="搜索最近简历"
          placeholder="搜索简历"
          title="输入关键词，按回车查看简历"
          @keydown.enter="router.push('/resumes')"
          type="search"
      /></label>
      <button
        type="button"
        class="icon-button header-help"
        aria-label="使用帮助"
        @click="emit('help')"
      >
        <CircleHelp :size="20" />
      </button>
      <button
        type="button"
        class="icon-button notification-button"
        aria-label="查看通知"
        @click="notify('欢迎来到简立得！当前为演示模式，没有新的通知。')"
      >
        <Bell :size="20" />
      </button>
      <span class="topbar-divider" />
      <button type="button" class="header-account" @click="router.push('/profile')">
        <span class="avatar avatar-small"
          ><img v-if="state.account.avatar" :src="state.account.avatar" alt="" /><template v-else>{{
            state.account.initials
          }}</template></span
        ><span>{{ state.account.nickname }}</span
        ><ChevronDown :size="14" />
      </button>
    </div>
  </header>
</template>
