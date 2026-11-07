<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '../composables/useAppStore';
import gsap from 'gsap';
import { ArrowRight, Eye, EyeOff, Sparkles } from '@lucide/vue';
import BaseButton from '../components/common/BaseButton.vue';
import TiltCard from '../components/common/TiltCard.vue';
const route = useRoute(),
  router = useRouter(),
  { login } = useAppStore();
const register = computed(() => route.path === '/register');
const authRoot = ref<HTMLElement | null>(null);
let entranceContext: gsap.Context | undefined;
const email = ref(''),
  password = ref(''),
  nickname = ref(''),
  showPassword = ref(false),
  accepted = ref(false),
  error = ref('');
const busy = ref(false);
async function enter() {
  if (busy.value) return;
  error.value = '';
  if (register.value && !accepted.value) {
    error.value = '请确认创建账户';
    return;
  }
  busy.value = true;
  try {
    await login(
      email.value.trim(),
      password.value,
      register.value ? nickname.value.trim() : undefined,
    );
    password.value = '';
    const redirect = route.query.redirect;
    const destination =
      typeof redirect === 'string' &&
      redirect.startsWith('/') &&
      !redirect.startsWith('//') &&
      !/^\/(login|register)(?:[/?#]|$)/.test(redirect)
        ? redirect
        : '/dashboard';
    await router.replace(destination);
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败，请重试';
  } finally {
    busy.value = false;
  }
}
onMounted(() => {
  if (!authRoot.value) return;
  entranceContext = gsap.context(() => {
    const entrance = gsap.timeline({ defaults: { ease: 'power3.out' } });
    entrance
      .from('.auth-story > .brand', { autoAlpha: 0, y: 16, duration: 0.55 })
      .from(
        '.auth-form',
        { autoAlpha: 0, y: 22, scale: 0.975, filter: 'blur(8px)', duration: 0.72 },
        '-=0.2',
      );
  }, authRoot.value);
});
onBeforeUnmount(() => entranceContext?.revert());
</script>
<template>
  <div ref="authRoot" class="auth-page">
    <section class="auth-story">
      <RouterLink to="/login" class="brand"
        ><span class="brand-icon"><Sparkles :size="25" /></span
        ><span><strong>简立得</strong></span></RouterLink
      >
    </section>
    <section class="auth-form-area">
      <RouterLink v-if="register" to="/login" class="auth-back"
        >返回登录 <ArrowRight :size="15"
      /></RouterLink>
      <TiltCard class="auth-glass-card">
        <form class="auth-form" @submit.prevent="enter">
          <!-- <span class="feature-icon"><Sparkles :size="24" /></span>*/ -->
          <h1 class="wrap-heading">{{ register ? '开启你的职业可能' : '欢迎回来' }}</h1>
          <!-- <p>
            {{
              register
                ? '为下一段旅程，留一个属于自己的空间。'
                : '继续整理经历，向理想的工作更近一步。'
            }}
          </p> -->
          <label v-if="register" class="field"
            >昵称<ElInput
              v-model="nickname"
              required
              maxlength="30"
              autocomplete="nickname"
              placeholder="我们该如何称呼你？"
              aria-label="昵称" /></label
          ><label class="field"
            >邮箱<ElInput
              v-model="email"
              required
              autocomplete="email"
              placeholder="name@example.com"
              type="email"
              aria-label="邮箱" /></label
          ><label class="field"
            >密码
            <div class="password-input">
              <ElInput
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                :minlength="register ? 5 : 1"
                maxlength="128"
                :autocomplete="register ? 'new-password' : 'current-password'"
                placeholder="注册密码 5～128 位，允许纯数字"
                aria-label="密码"
              /><button
                type="button"
                class="icon-button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" :size="17" /><Eye v-else :size="17" />
              </button></div></label
          ><ElCheckbox v-if="register" class="check-label" v-model="accepted"
            >我确认使用此邮箱创建账户</ElCheckbox
          >
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <BaseButton type="submit" class="full-width" :loading="busy"
            >{{ register ? '注册并登录' : '登录' }}<ArrowRight :size="17"
          /></BaseButton>
          <p class="auth-switch">
            {{ register ? '已经有账户？' : '还没有账户？'
            }}<RouterLink :to="register ? '/login' : '/register'">{{
              register ? '返回登录' : '前往注册'
            }}</RouterLink>
          </p>
          <!-- <div class="demo-notice">
            <ShieldCheck :size="17" />登录状态保存在当前浏览器，7
            天后需重新登录。请勿在公用设备上保留登录。
          </div> -->
        </form>
      </TiltCard>
    </section>
  </div>
</template>

<style scoped>
.auth-page {
  --auth-periwinkle: #A7CEFC;
  --auth-pink: #FFE492;
  --auth-lavender: #A7CEFC;
  --auth-pearl: #FFFFFF;
  position: relative;
  isolation: isolate;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: none;
  min-height: 100dvh;
  margin: 0;
  padding: 96px 24px;
  overflow: hidden;
  background: #FFFFFF;
}
.auth-page::before {
  content: '';
  position: absolute;
  z-index: -1;
  inset: -12%;
  background:
    radial-gradient(ellipse 44% 52% at 17% 35%, var(--auth-periwinkle), transparent 74%),
    radial-gradient(ellipse 42% 48% at 83% 26%, var(--auth-pink), transparent 74%),
    radial-gradient(ellipse 50% 44% at 59% 85%, var(--auth-lavender), transparent 78%),
    radial-gradient(ellipse 44% 48% at 48% 20%, var(--auth-pearl), transparent 82%);
  opacity: 0.8;
  filter: blur(64px);
  pointer-events: none;
}
.auth-story {
  position: absolute;
  inset: 28px auto auto 36px;
  display: block;
  width: auto;
  padding: 0;
  overflow: visible;
  background: transparent;
}
.auth-story::after {
  content: none;
}
.auth-story > .brand {
  margin: 0;
  gap: 12px;
}
.auth-story .brand strong {
  color: #37A3FF;
  font-size: 23px;
  font-weight: 700;
}
.auth-story .brand-icon {
  width: 42px;
  height: 42px;
  color: #37A3FF;
  border: 1px solid #FFFFFFb3;
  border-radius: 13px;
  background: #FFFFFF80;
  box-shadow: 0 4px 16px #37A3FF12;
}
.auth-form-area {
  position: static;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-width: 0;
  min-height: 0;
  padding: 0;
}
.auth-glass-card {
  width: min(100%, 560px);
  border: 1px solid #FFFFFFe0;
  border-radius: 28px;
  background: #FFFFFF61;
  backdrop-filter: blur(28px) saturate(135%);
  -webkit-backdrop-filter: blur(28px) saturate(135%);
  box-shadow:
    0 24px 80px #37A3FF24,
    0 4px 16px #37A3FF0a,
    inset 0 1px 0 #FFFFFFcc;
}
.auth-form {
  width: 100%;
  max-width: none;
  padding: 64px 48px;
  border: 0;
  border-radius: inherit;
  background: transparent;
  box-shadow: none;
}
.auth-form > .feature-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin: 0 auto 20px;
  border: 1px solid #FFFFFFb3;
  border-radius: 15px;
  color: #4F9CF9;
  background: #FFFFFF70;
  box-shadow: 0 4px 12px #37A3FF12;
}
.auth-form > h1 {
  max-width: none;
  margin: 0 0 72px;
  color: #212529;
  font-size: 36px;
  font-weight: 650;
  line-height: 1.2;
  letter-spacing: -0.035em;
  /* text-align: center; */
}
.auth-form > p:not(.auth-switch):not(.form-error) {
  margin: 0 0 32px;
  color: #212529;
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
}
.auth-form .field {
  gap: 10px;
  margin-bottom: 22px;
  color: #212529;
  font-size: 14px;
  font-weight: 500;
}
.auth-form .field input:not([type='checkbox']):not([type='range']):not([type='color']),
.auth-form .password-input {
  min-height: 52px;
  border: 1px solid #FFFFFFb8;
  border-radius: 12px;
  background: #FFFFFF66;
  box-shadow:
    0 1px 3px #37A3FF05,
    inset 0 1px 0 #FFFFFFa6;
  transition:
    border-color 180ms ease,
    background-color 180ms ease,
    box-shadow 180ms ease;
}
.auth-form .field input:not([type='checkbox']):not([type='range']):not([type='color']) {
  padding: 14px 16px;
  color: #37A3FF;
}
.auth-form .password-input input:not([type='checkbox']):not([type='range']):not([type='color']) {
  border: 0;
  box-shadow: none;
  padding-left: 16px;
  background: transparent;
  color: #37A3FF;
}
.auth-form input::placeholder {
  color: #212529;
  font-weight: 400;
}
.auth-form .field > input:focus,
.auth-form .password-input:focus-within {
  border-color: #A7CEFC;
  outline: none;
  background: #FFFFFF9c;
  box-shadow: 0 0 0 3px #A7CEFC24;
}
.auth-form .password-input input:focus {
  outline: none;
  box-shadow: none;
}
.auth-form > .base-button {
  min-height: 50px;
  margin-top: 6px;
  border-color: #FFFFFFc7;
  background: #FFFFFF94;
  box-shadow: 0 4px 16px #A7CEFC12;
  font-size: 15px;
}
.auth-switch {
  margin-top: 24px;
  color: #212529;
  text-align: center;
}
.auth-switch a {
  color: #37A3FF;
  font-weight: 600;
}
.auth-form .demo-notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 28px;
  padding: 20px 0 0;
  border: 0;
  border-top: 1px solid #FFFFFF8f;
  border-radius: 0;
  color: #212529;
  background: transparent;
  font-size: 12px;
  line-height: 1.8;
  text-align: left;
}
.auth-form .demo-notice > svg {
  flex: 0 0 16px;
  margin: 2px 0 0;
}
.auth-back {
  top: 38px;
  right: 36px;
  color: #37A3FF;
}
.auth-form .form-error {
  color: var(--color-error);
  text-align: left;
}
@media (max-width: 600px) {
  .auth-page {
    padding: 104px 20px 40px;
  }
  .auth-page::before {
    inset: -5% -55%;
    filter: blur(48px);
  }
  .auth-story {
    top: 24px;
    left: 24px;
  }
  .auth-story .brand strong {
    font-size: 21px;
  }
  .auth-glass-card {
    border-radius: 24px;
  }
  .auth-form {
    padding: 32px 24px 28px;
  }
  .auth-form > h1 {
    font-size: 30px;
  }
  .auth-form > p:not(.auth-switch):not(.form-error) {
    margin-bottom: 28px;
  }
  .auth-back {
    top: 36px;
    right: 24px;
    font-size: 13px;
  }
}
@supports not (backdrop-filter: blur(1px)) {
  .auth-glass-card {
    background: #FFFFFFd9;
  }
}
</style>
