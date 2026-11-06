<script setup lang="ts">
import {
  BriefcaseBusiness,
  ChevronRight,
  CircleHelp,
  FileText,
  FolderClosed,
  MessageSquare,
  Sparkles,
  UserRound,
  X,
} from '@lucide/vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { useAppStore } from '../../composables/useAppStore';

defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: []; help: [] }>();
const { state } = useAppStore();
const route = useRoute(),
  router = useRouter();
const navigation = [
  { title: 'AI简历生成', path: '/dashboard', icon: Sparkles },
  { title: '我的简历', path: '/resumes', icon: FileText },
  { title: '岗位匹配', path: '/jobs', icon: BriefcaseBusiness },
  { title: '模拟面试', path: '/interview', icon: MessageSquare },
  { title: '岗位 JD 档案', path: '/jd-library', icon: FolderClosed },
];
</script>

<template>
  <button
    v-if="open"
    type="button"
    class="sidebar-backdrop"
    aria-label="关闭导航菜单"
    @click="emit('close')"
  />
  <aside
    id="main-sidebar"
    class="sidebar"
    :class="{ 'sidebar-open': open }"
    :role="open ? 'dialog' : undefined"
    :aria-modal="open || undefined"
    aria-label="主导航"
  >
    <RouterLink class="brand" to="/dashboard" @click="emit('close')">
      <span class="brand-icon"><Sparkles :size="25" :stroke-width="1.8" /></span>
      <span><strong>简立得</strong><small>Resumind</small></span>
    </RouterLink>
    <button
      type="button"
      class="icon-button mobile-close"
      aria-label="收起导航"
      @click="emit('close')"
    >
      <X :size="20" />
    </button>
    
    <nav class="primary-nav">
      <RouterLink
        v-for="item in navigation"
        :key="item.path"
        :to="item.path"
        class="nav-link"
        :class="{
          'nav-link-current': route.path === item.path || route.path.startsWith(item.path + '/'),
        }"
        @click="emit('close')"
      >
        <component :is="item.icon" :size="19" :stroke-width="1.75" />
        <span>{{ item.title }}</span>
      </RouterLink>
    </nav>
    <div class="sidebar-bottom">

      <div class="sidebar-utility">
        <RouterLink to="/profile" class="nav-link" @click="emit('close')"
          ><UserRound :size="18" /><span>个人中心</span></RouterLink
        >
        <button
          type="button"
          class="nav-link"
          @click="
            emit('help');
            emit('close');
          "
        >
          <CircleHelp :size="18" /><span>帮助与反馈</span>
        </button>
      </div>
      <button
        type="button"
        class="sidebar-account"
        @click="
          router.push('/profile');
          emit('close');
        "
      >
        <span class="avatar"
          ><img v-if="state.account.avatar" :src="state.account.avatar" alt="" /><template v-else>{{
            state.account.initials
          }}</template></span
        ><span class="account-text"
          ><strong>{{ state.account.nickname }}</strong
          ><small>开启你的职业可能</small></span
        ><ChevronRight :size="16" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
/* Hallmark · shape: app screen · genre: modern-minimal · theme: brand · redesign: full · v2.0.0 */
/* Hallmark · pre-emit critique: P4 H5 E4 S4 R5 V3 · weakest: V, kept shared workspace shell */
.account-text {
  min-width: 0;
}
</style>
