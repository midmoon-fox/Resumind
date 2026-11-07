<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router';
import { ArrowRight, Sparkles } from '@lucide/vue';
import ParticlesBg from '../components/ui/ParticlesBg.vue';
import BreathingText from '../components/ui/BreathingText.vue';
import FluidCursor from '../components/ui/FluidCursor.vue';
import { authRedirect } from '../router/authRedirect';

const route = useRoute();
const showEffects = window.matchMedia('(prefers-reduced-motion: no-preference)').matches;
function authTarget(name: 'login' | 'register') {
  const redirect = authRedirect(route.query.redirect);
  return {
    name,
    query: redirect ? { redirect } : {},
  };
}
</script>

<template>
  <main class="welcome-page">
    <ParticlesBg
      v-if="showEffects"
      class="particles-background-layer"
      :quantity="92"
      :staticity="18"
      :ease="10"
    />
    <FluidCursor
      v-if="showEffects"
      class="fluid-cursor-layer"
      :dye-resolution="768"
      :splat-force="5200"
      :splat-radius="0.16"
      :color-update-speed="7"
    />
    <div class="welcome-glow welcome-glow-one" aria-hidden="true"></div>
    <div class="welcome-glow welcome-glow-two" aria-hidden="true"></div>
    <section class="welcome-content" aria-labelledby="welcome-title">
      <div class="welcome-badge">
        <Sparkles :size="16" /> 简立得 · 让求职从容一点 <ArrowRight :size="15" />
      </div>
      <p class="welcome-eyebrow">RESUME, MADE PERSONAL</p>
      <BreathingText id="welcome-title" class="welcome-title" text="你的专属简历，即刻拥有" />
      <p class="welcome-subtitle">Your exclusive resume, instantly yours</p>
      <div class="landing-actions">
        <RouterLink class="welcome-button welcome-button-primary" :to="authTarget('login')"
          >登录 <ArrowRight :size="18"
        /></RouterLink>
        <RouterLink class="welcome-button welcome-button-secondary" :to="authTarget('register')"
          >注册 <ArrowRight :size="18"
        /></RouterLink>
      </div>
      <div class="welcome-orbit" aria-hidden="true"><span></span><i></i></div>
      <p class="welcome-footnote">把你的经历，写成下一段可能</p>
    </section>
  </main>
</template>

<style scoped>
.welcome-page {
  position: relative;
  display: grid;
  min-height: 100vh;
  min-height: 100svh;
  overflow: hidden;
  place-items: center;
  isolation: isolate;
  color: var(--color-ink);
  background:
    radial-gradient(
      ellipse at 50% 110%,
      color-mix(in srgb, var(--color-paper-4) 62%, transparent),
      transparent 43%
    ),
    radial-gradient(
      ellipse at 8% 14%,
      color-mix(in srgb, var(--color-accent) 30%, transparent),
      transparent 34%
    ),
    radial-gradient(
      ellipse at 92% 18%,
      color-mix(in srgb, var(--color-paper-4) 42%, transparent),
      transparent 35%
    ),
    var(--color-paper-2);
}
.particles-background-layer {
  position: absolute;
  z-index: 0;
  inset: 0;
  opacity: 0.54;
  pointer-events: none;
}
.welcome-glow {
  position: absolute;
  z-index: -1;
  width: 34rem;
  aspect-ratio: 1;
  border: 1px solid color-mix(in srgb, var(--color-accent) 16%, transparent);
  border-radius: 50%;
  pointer-events: none;
}
.welcome-glow::before,
.welcome-glow::after {
  position: absolute;
  content: '';
  border: 1px solid color-mix(in srgb, var(--color-paper-4) 24%, transparent);
  border-radius: 50%;
  inset: 8%;
  transform: rotate(-18deg) scaleY(0.4);
}
.welcome-glow::after {
  inset: 17%;
  transform: rotate(26deg) scaleY(0.52);
}
.welcome-glow-one {
  left: -19rem;
  top: 8%;
  transform: rotate(-20deg) scaleY(0.64);
}
.welcome-glow-two {
  right: -20rem;
  bottom: -18rem;
  transform: rotate(25deg) scaleY(0.66);
}
.welcome-content {
  position: relative;
  z-index: 2;
  display: block;
  width: min(100% - 32px, 1200px);
  padding: 86px 0 64px;
  text-align: center;
  visibility: visible;
  opacity: 1;
}
.welcome-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 17px;
  border: 1px solid color-mix(in srgb, var(--color-accent-border) 20%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-paper) 58%, transparent);
  color: var(--color-ink-2);
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 8px 32px color-mix(in srgb, var(--color-ink) 6%, transparent);
  backdrop-filter: blur(14px);
}
.welcome-badge :deep(svg:first-child) {
  color: var(--color-accent);
}
.welcome-eyebrow {
  margin: 48px 0 16px;
  color: var(--color-accent-text);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.24em;
}
:deep(.welcome-title) {
  display: block;
  max-width: none;
  white-space: nowrap;
  color: var(--color-ink);
  font-size: clamp(24px, 5vw, 62px);
  font-weight: 750;
  line-height: 1.13;
  letter-spacing: -0.065em;
}
.welcome-subtitle {
  margin-top: 22px;
  color: var(--color-muted);
  font-size: clamp(16px, 2vw, 21px);
  letter-spacing: 0.005em;
}
.landing-actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 18px;
  margin-top: 46px;
}
.welcome-button {
  display: inline-flex;
  min-width: 220px;
  min-height: 62px;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border: 1px solid transparent;
  border-radius: 17px;
  font-size: 17px;
  font-weight: 650;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}
.welcome-button:hover {
  transform: translateY(-3px);
}
.welcome-button-primary {
  color: var(--color-accent-ink);
  background: linear-gradient(120deg, var(--color-accent), var(--color-accent-hover));
  box-shadow: 0 12px 30px color-mix(in srgb, var(--color-accent-hover) 28%, transparent);
}
.welcome-button-primary:hover {
  box-shadow: 0 16px 36px color-mix(in srgb, var(--color-accent-hover) 36%, transparent);
}
.welcome-button-secondary {
  border-color: color-mix(in srgb, var(--color-accent-border) 22%, transparent);
  color: var(--color-ink-2);
  background: color-mix(in srgb, var(--color-paper) 72%, transparent);
  box-shadow: 0 10px 28px color-mix(in srgb, var(--color-ink) 8%, transparent);
  backdrop-filter: blur(12px);
}
.welcome-orbit {
  position: relative;
  width: min(430px, 70vw);
  height: 124px;
  margin: 52px auto 0;
  overflow: hidden;
  border-radius: 50% 50% 0 0 / 82% 82% 0 0;
  background: radial-gradient(
    ellipse at 50% 100%,
    color-mix(in srgb, var(--color-paper) 90%, transparent) 0,
    color-mix(in srgb, var(--color-paper-4) 46%, transparent) 38%,
    transparent 72%
  );
  filter: drop-shadow(0 -9px 20px color-mix(in srgb, var(--color-accent-hover) 16%, transparent));
}
.welcome-orbit::before {
  position: absolute;
  content: '';
  inset: 18px 0 -86px;
  border: 1px solid color-mix(in srgb, var(--color-accent-border) 22%, transparent);
  border-radius: 50%;
}
.welcome-orbit::after {
  position: absolute;
  content: '';
  inset: 27px 14px -84px;
  border: 1px dashed color-mix(in srgb, var(--color-accent-border) 26%, transparent);
  border-radius: 50%;
}
.welcome-orbit span,
.welcome-orbit i {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-accent);
  box-shadow:
    33px 12px var(--color-accent-border),
    68px 2px var(--color-accent-hover),
    105px 23px var(--color-accent-border),
    145px 7px var(--color-accent),
    184px 24px var(--color-accent-border),
    223px 3px var(--color-accent-hover),
    270px 21px var(--color-accent-border),
    310px 7px var(--color-accent-hover),
    350px 25px var(--color-accent-border);
  top: 55px;
  left: 9%;
}
.welcome-orbit i {
  top: 72px;
  left: 14%;
  transform: scale(0.7);
  opacity: 0.55;
}
.welcome-footnote {
  margin-top: 9px;
  color: var(--color-muted);
  font-size: 13px;
  letter-spacing: 0.08em;
}
@media (max-width: 640px) {
  .welcome-content {
    padding-top: 62px;
  }
  .welcome-eyebrow {
    margin-top: 40px;
  }
  :deep(.welcome-title) {
    font-size: clamp(21px, 5.5vw, 34px);
    letter-spacing: -0.055em;
  }
  .landing-actions {
    gap: 12px;
    margin-top: 34px;
  }
  .welcome-button {
    min-width: 0;
    width: min(44vw, 190px);
    min-height: 56px;
    border-radius: 14px;
  }
  .welcome-orbit {
    margin-top: 58px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .welcome-button {
    transition: none;
  }
}
</style>
