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
import Logo from '../../assets/Logo.png';

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
  { title: '岗位需求档案', path: '/jd-library', icon: FolderClosed },
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
      <span class="brand-icon"><img :src="Logo" alt="" /></span>
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
          ></span
        ><ChevronRight :size="16" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  left: 0;
  height: 100dvh;
  padding: 12px 8px 8px;
  color: #1e1e1e;
  background: #ffffff;
  border-right: 1px solid #e6e6e6;
  font-family: Inter, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  box-shadow: none;
}

.sidebar .brand {
  min-height: 56px;
  margin: 0 4px 16px;
  padding: 4px 8px;
  gap: 12px;
}

.sidebar .brand-icon {
  width: 52px;
  height: 52px;
  border: 0;
  border-radius: 8px;
  /* color: #275e9b; */
  background:#ffffff;
  box-shadow: none;
  transform: none;
}

.sidebar .brand-icon svg {
  width: 22px;
  height: 22px;
}

.sidebar .brand strong {
  color: #3487ed;
  font-size: 16px;
  line-height: 22px;
  font-weight: 600;
}

.sidebar .brand small {
  margin-top: 0;
  color: #3487ed;
  font-size: 12px;
  line-height: 18px;
}

.primary-nav,
.sidebar-utility {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar .nav-link {
  min-height: 40px;
  padding: 8px 12px;
  gap: 12px;
  border-radius: 6px;
  color: #1e1e1e;
  background: transparent;
  font-size: 14px;
  line-height: 24px;
  font-weight: 400;
  box-shadow: none;
  transform: none;
  transition: background-color 120ms ease;
}

.sidebar .nav-link svg {
  width: 20px;
  height: 20px;
  color: #444444;
}

.sidebar .nav-link:hover {
  color: #1e1e1e;
  background: #f5f5f5;
  transform: none;
}

.sidebar .nav-link-current,
.sidebar .nav-link-current:hover,
.sidebar-utility .router-link-exact-active {
  color: #1e1e1e;
  background: #e5f2ff;
  box-shadow: none;
}

.sidebar .nav-link-current svg {
  color: #444444;
}

.sidebar .nav-link::before {
  content: none;
}

.sidebar-bottom {
  padding-top: 24px;
}

.sidebar-utility {
  padding-bottom: 12px;
}

.sidebar .sidebar-account {
  width: 100%;
  min-height: 60px;
  margin: 0;
  padding: 12px;
  gap: 10px;
  border: 0;
  border-top: 1px solid #e6e6e6;
  border-radius: 0;
  color: #1e1e1e;
  background: #ffffff;
  box-shadow: none;
}

.sidebar .sidebar-account:hover {
  background: #f5f5f5;
}

.sidebar .avatar {
  width: 28px;
  height: 28px;
  border: 0;
  color: #275e9b;
  background: #e5f2ff;
  font-size: 12px;
}

.account-text {
  min-width: 0;
}

.sidebar .account-text strong {
  color: #1e1e1e;
  font-size: 13px;
  line-height: 20px;
  font-weight: 500;
}

.sidebar .account-text small {
  margin-top: 0;
  color: #767676;
  font-size: 11px;
  line-height: 16px;
}
</style>
