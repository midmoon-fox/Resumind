import { createRouter, createWebHistory } from 'vue-router';
import DashboardView from '../views/DashboardView.vue';
import { useAppStore } from '../composables/useAppStore';
import { useToast } from '../composables/useToast';
import { authRedirect } from './authRedirect';
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: () => import('../views/LandingView.vue'),
      meta: { title: '你的专属简历，即刻拥有', landingPage: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      meta: { title: 'AI简历生成' },
    },
    {
      path: '/resumes',
      name: 'resumes',
      component: () => import('../views/ResumesView.vue'),
      meta: { title: '我的简历' },
    },
    {
      path: '/resumes/:id/edit',
      name: 'editor',
      component: () => import('../views/EditorView.vue'),
      meta: { title: '简历编辑器' },
    },
    {
      path: '/create',
      name: 'create',
      component: () => import('../views/CreateView.vue'),
      meta: { title: '制作简历', creationSession: true },
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: () => import('../views/JobsView.vue'),
      meta: { title: '岗位匹配' },
    },
    {
      path: '/interview',
      name: 'interview',
      component: () => import('../views/InterviewView.vue'),
      meta: { title: '模拟面试' },
    },
    {
      path: '/jd-library',
      name: 'jd-library',
      component: () => import('../views/JdLibraryView.vue'),
      meta: { title: '岗位 JD 档案' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { title: '个人中心' },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/AuthView.vue'),
      meta: { title: '登录', authPage: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/AuthView.vue'),
      meta: { title: '注册', authPage: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
      meta: { title: '页面未找到' },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
});
router.beforeEach(async (to, from) => {
  if (to.meta.landingPage && !from.name) return true;
  const { state, initialize, flushAll, discardWorkspace } = useAppStore();
  if (!to.meta.landingPage) await initialize();
  try {
    await flushAll();
  } catch (cause) {
    useToast().error(
      '当前修改未能保存，暂时无法切换页面。' +
        (cause instanceof Error ? cause.message : '请重试保存。'),
    );
    return false;
  }
  if (to.meta.landingPage) return true;
  if (to.meta.authPage)
    return state.demoSignedIn ? (authRedirect(to.query.redirect) ?? '/dashboard') : true;
  if (!state.demoSignedIn) return { name: 'landing', query: { redirect: to.fullPath } };
  if (to.name === 'create' && from.name !== 'create') {
    discardWorkspace();
    const jd = state.jds.find((j) => j.id === to.query.jdId && j.version?.status === 'CONFIRMED');
    if (jd) {
      state.workspace.jdId = jd.id;
      state.workspace.direction = jd.version?.jobTitle || jd.title;
    } else if (typeof to.query.direction === 'string') {
      state.workspace.direction = to.query.direction.trim().slice(0, 100);
    }
  }
  return true;
});
router.afterEach((to, from, failure) => {
  if (!failure && from.name === 'create' && to.name !== 'create') useAppStore().discardWorkspace();
  document.title = String(to.meta.title || '简立得') + ' · 简立得';
});
router.onError((cause) => {
  console.error('页面切换失败', cause);
  useToast().error('页面加载失败，未能完成跳转。请稍后重试；若仍失败，请刷新页面。');
});
export default router;
