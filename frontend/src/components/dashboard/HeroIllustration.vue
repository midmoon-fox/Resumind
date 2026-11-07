<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue';
const habitat = ref<HTMLElement>();
const speechId = useId();
const paused = ref(false),
  hidden = ref(false),
  offscreen = ref(false),
  reducedMotion = ref(false);
const happy = ref(false),
  reaction = ref(0),
  eyeX = ref(0),
  eyeY = ref(0),
  bodyX = ref(0),
  bodyY = ref(0),
  tilt = ref(0);
const messages = [
  '我是泡泡，陪你慢慢准备。',
  '摸摸收到！今天也一起加油。',
  '不用一次完美，先写下一段真实经历。',
  '每一个小进步，都值得开心一下。',
  '准备好了？我们一起出发吧。',
];
const speech = computed(() =>
  paused.value ? '休息一下也很好，我就在这里。' : messages[reaction.value % messages.length],
);
const resting = computed(() => paused.value || hidden.value || offscreen.value);
let resetTimer: ReturnType<typeof setTimeout> | undefined;
let pointerFrame = 0;
let media: MediaQueryList | undefined;
let observer: IntersectionObserver | undefined;
let followArea: HTMLElement | null = null;
function pet() {
  reaction.value += 1;
  happy.value = true;
  clearTimeout(resetTimer);
  resetTimer = setTimeout(() => (happy.value = false), 1100);
}
function followPointer(event: PointerEvent) {
  if (event.pointerType === 'touch' || resting.value || reducedMotion.value || pointerFrame) return;
  const { clientX, clientY } = event;
  pointerFrame = requestAnimationFrame(() => {
    pointerFrame = 0;
    if (resting.value || reducedMotion.value) return;
    const bounds = habitat.value?.querySelector('.pet-stage')?.getBoundingClientRect();
    if (!bounds) return;
    const x = Math.max(-1, Math.min(1, (clientX - bounds.left - bounds.width / 2) / 180));
    const y = Math.max(-1, Math.min(1, (clientY - bounds.top - bounds.height / 2) / 130));
    eyeX.value = x * 10;
    eyeY.value = y * 7;
    bodyX.value = x * 18;
    bodyY.value = y * 10;
    tilt.value = x * 7;
  });
}
function resetEyes() {
  cancelAnimationFrame(pointerFrame);
  pointerFrame = 0;
  eyeX.value = 0;
  eyeY.value = 0;
  bodyX.value = 0;
  bodyY.value = 0;
  tilt.value = 0;
}
function syncVisibility() {
  hidden.value = document.hidden;
  if (hidden.value) resetEyes();
}
function syncMotion() {
  reducedMotion.value = Boolean(media?.matches);
  if (reducedMotion.value) resetEyes();
}
onMounted(() => {
  media = window.matchMedia('(prefers-reduced-motion: reduce)');
  syncMotion();
  syncVisibility();
  followArea = habitat.value?.closest<HTMLElement>('.hero-banner') ?? habitat.value ?? null;
  followArea?.addEventListener('pointermove', followPointer, { passive: true });
  followArea?.addEventListener('pointerleave', resetEyes);
  media.addEventListener('change', syncMotion);
  document.addEventListener('visibilitychange', syncVisibility);
  observer = new IntersectionObserver(([entry]) => {
    offscreen.value = !entry?.isIntersecting;
    if (offscreen.value) resetEyes();
  });
  if (habitat.value) observer.observe(habitat.value);
});
onBeforeUnmount(() => {
  clearTimeout(resetTimer);
  cancelAnimationFrame(pointerFrame);
  observer?.disconnect();
  followArea?.removeEventListener('pointermove', followPointer);
  followArea?.removeEventListener('pointerleave', resetEyes);
  media?.removeEventListener('change', syncMotion);
  document.removeEventListener('visibilitychange', syncVisibility);
});
</script>
<template>
  <section
    ref="habitat"
    class="pet-habitat"
    :class="{ 'pet-resting': resting, 'pet-happy': happy }"
    aria-label="求职搭子泡泡"
    :style="{
      '--pet-body-x': bodyX + 'px',
      '--pet-body-y': bodyY + 'px',
      '--pet-tilt': tilt + 'deg',
    }"
  >
    <div class="pet-header">
      <!-- <span class="pet-label"><Sparkles :size="14" aria-hidden="true" />你的求职搭子</span> -->
      <!-- <button
        type="button"
        class="pet-motion-toggle"
        :aria-label="paused ? '播放桌宠动画' : '暂停桌宠动画'"
        :aria-pressed="paused"
        :title="paused ? '播放桌宠动画' : '暂停桌宠动画'"
        @click="
          paused = !paused;
          resetEyes();
        "
      >
        <Play v-if="paused" :size="14" aria-hidden="true" /><Pause
          v-else
          :size="14"
          aria-hidden="true"
        />
      </button> -->
    </div>
    <div class="pet-stage">
      <span class="pet-ground" aria-hidden="true" />
      <button
        type="button"
        class="pet-touch"
        aria-label="摸摸泡泡"
        :aria-describedby="speechId"
        :style="{ '--pet-eye-x': eyeX + 'px', '--pet-eye-y': eyeY + 'px' }"
        @click="pet"
        @blur="resetEyes"
      >
        <span class="pet-float" aria-hidden="true"
          ><span class="pet-squish">
            <span class="pet-hand pet-hand-left" /><span class="pet-hand pet-hand-right" />
            <span class="pet-jelly"
              ><span class="pet-face">
                <span class="pet-eye pet-eye-left" /><span class="pet-eye pet-eye-right" />
                <span class="pet-cheek pet-cheek-left" /><span
                  class="pet-cheek pet-cheek-right"
                /><span class="pet-smile" /> </span
            ></span>
            <span class="pet-foot pet-foot-left" /><span class="pet-foot pet-foot-right" /> </span
        ></span>
        <span v-if="happy" :key="reaction" class="pet-affection" aria-hidden="true"
          ><span>♡</span><span>✧</span><span>♡</span></span
        >
      </button>
    </div>
    <p :id="speechId" class="pet-speech" role="status" aria-live="polite" aria-atomic="true">
      {{ speech }}
    </p>

  </section>
</template>
<style scoped>
.hero-art.pet-habitat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-width: 0;
  height: 310px;
  padding: 14px 20px 16px;
  /* border: 1px solid #ffffffe0; */
  border-radius: 26px;
  /* background: linear-gradient(145deg, #ffffff78, #f0f7ff42 60%, #ddeaf440); */
  /* box-shadow:
    inset 0 1px 0 #fff,
    inset 0 -1px 0 #ffffff70,
    0 16px 40px #48657b12; */
  /* backdrop-filter: blur(12px); */
  /* -webkit-backdrop-filter: blur(12px); */
}
.hero-art.pet-habitat::after {
  content: none;
}
.pet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  align-self: stretch;
  min-height: 30px;
}
.pet-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #526a80;
}
.pet-motion-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid #ffffffc9;
  border-radius: 50%;
  color: #48657b;
  background: #ffffff78;
  box-shadow: inset 0 1px 0 #fff;
}
.pet-motion-toggle:hover {
  background: #fff;
}
.pet-stage {
  position: relative;
  display: grid;
  place-items: center;
  width: 100%;
  height: 170px;
  flex-shrink: 0;
}
.pet-touch {
  transform: translate3d(var(--pet-body-x, 0px), var(--pet-body-y, 0px), 0)
    rotate(var(--pet-tilt, 0deg)) scale(var(--pet-scale, 1));
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
  z-index: 1;
  width: 190px;
  height: 178px;
  padding: 0;
  border: 0;
  border-radius: 45%;
  background: transparent;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.pet-touch:focus-visible,
.pet-motion-toggle:focus-visible,
.pet-resume-link:focus-visible {
  outline: 3px solid var(--color-focus);
  outline-offset: 4px;
}
.pet-float {
  position: absolute;
  inset: 0;
  animation: pet-float 5s ease-in-out infinite;
}
.pet-squish {
  position: absolute;
  inset: 0;
  transform-origin: 50% 85%;
}
.pet-jelly {
  position: absolute;
  z-index: 2;
  left: 21px;
  top: 9px;
  width: 148px;
  height: 145px;
  border: 1.5px solid #ffffffe6;
  border-radius: 48% 52% 46% 44% / 50% 48% 50% 48%;
  background:
    radial-gradient(ellipse at 30% 14%, #ffffffeb, transparent 44%),
    radial-gradient(ellipse at 19% 77%, #cec4f3a6, transparent 52%),
    radial-gradient(ellipse at 76% 52%, #5ec5f7b3, transparent 64%),
    linear-gradient(145deg, #c4f3ff91, #9cd9fbcc 58%, #d8efff99);
  box-shadow:
    inset 5px 7px 15px #ffffffc9,
    inset -5px -8px 18px #7fb6d447,
    inset 0 -3px 6px #ffffffa6,
    0 12px 26px #6095b524;
}
.pet-jelly::before {
  content: '';
  position: absolute;
  left: 21px;
  top: 12px;
  width: 61px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(180deg, #ffffffc7, #ffffff00);
  transform: rotate(-25deg);
  filter: blur(1px);
}
.pet-jelly::after {
  content: '';
  position: absolute;
  inset: 8px 9px;
  border: 1px solid #ffffff33;
  border-bottom-color: #ffffffb3;
  border-radius: inherit;
  pointer-events: none;
}
.pet-face {
  position: absolute;
  inset: 0;
  transform: translate(var(--pet-eye-x, 0px), var(--pet-eye-y, 0px));
}
.pet-eye {
  position: absolute;
  top: 59px;
  width: 12px;
  height: 23px;
  border-radius: 9px;
  background: #355a74;
  box-shadow: 0 1px 1px #ffffffb3;
  transform-origin: center;
  animation: pet-blink 6s infinite;
}
.pet-eye::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 4px;
  height: 6px;
  border-radius: 50%;
  background: #ffffffe0;
}
.pet-eye-left {
  left: 44px;
}
.pet-eye-right {
  right: 40px;
}
.pet-cheek {
  position: absolute;
  top: 85px;
  width: 18px;
  height: 8px;
  background: #ac9fdf40;
  border-radius: 50%;
}
.pet-cheek-left {
  left: 24px;
}
.pet-cheek-right {
  right: 20px;
}
.pet-smile {
  position: absolute;
  top: 84px;
  left: 66px;
  width: 16px;
  height: 10px;
  border: 2px solid #527892;
  border-top: 0;
  border-radius: 0 0 12px 12px;
}
.pet-hand,
.pet-foot {
  position: absolute;
  border: 1px solid #ffffffe0;
  background: linear-gradient(135deg, #edfbffdb, #8bcced99);
  box-shadow: inset 2px 2px 4px #ffffffa6;
  border-radius: 50%;
}
.pet-hand {
  z-index: 1;
  top: 98px;
  width: 28px;
  height: 40px;
}
.pet-hand-left {
  left: 9px;
  transform: rotate(32deg);
}
.pet-hand-right {
  right: 8px;
  transform: rotate(-32deg);
}
.pet-foot {
  z-index: 3;
  top: 142px;
  width: 35px;
  height: 17px;
}
.pet-foot-left {
  left: 41px;
  transform: rotate(-8deg);
}
.pet-foot-right {
  right: 36px;
  transform: rotate(8deg);
}
.pet-ground {
  position: absolute;
  width: 116px;
  height: 16px;
  bottom: 2px;
  border-radius: 50%;
  background: #7697b12b;
  filter: blur(6px);
}
.pet-name {
  position: absolute;
  right: calc(50% - 112px);
  top: 23px;
  color: #5f7e96;
  font-size: 11px;
  letter-spacing: 0.15em;
  transform: rotate(9deg);
}
.pet-speech {
  position: relative;
  z-index: 1;
  font-size: 13px;
  line-height: 1.7;
  color: #3d5b73;
  text-align: center;
  min-height: 23px;
  max-width: 100%;
}
.pet-resume-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 30px;
  padding: 3px 12px;
  border: 1px solid #ffffffbf;
  border-radius: 999px;
  color: #355f82;
  background: #ffffff70;
  font-size: 12px;
}
.pet-resume-link:hover {
  background: #fff;
}
.pet-hint {
  font-size: 11px;
  color: #526a80;
  line-height: 1.6;
  text-align: center;
}
.pet-affection {
  position: absolute;
  z-index: 4;
  top: 12px;
  inset-inline: 0;
  pointer-events: none;
  color: #729ac0;
  font-size: 24px;
}
.pet-affection span {
  position: absolute;
  animation: pet-affection 1s ease-out both;
}
.pet-affection span:nth-child(1) {
  left: 14px;
  --heart-turn: -15deg;
}
.pet-affection span:nth-child(2) {
  left: 87px;
  top: -10px;
  animation-delay: 80ms;
  --heart-turn: 8deg;
}
.pet-affection span:nth-child(3) {
  right: 4px;
  top: 18px;
  animation-delay: 130ms;
  --heart-turn: 15deg;
}
.pet-happy .pet-squish {
  animation: pet-jump 650ms cubic-bezier(0.22, 1, 0.36, 1);
}
.pet-happy .pet-smile {
  height: 14px;
  background: #52789215;
}
.pet-happy .pet-hand-right {
  transform: translateY(-10px) rotate(-66deg);
}
.pet-resting .pet-float,
.pet-resting .pet-eye,
.pet-resting .pet-squish,
.pet-resting .pet-affection span {
  animation-play-state: paused;
}
@keyframes pet-float {
  0%,
  100% {
    transform: translateY(1px) rotate(-2deg);
  }
  50% {
    transform: translateY(-8px) rotate(2deg);
  }
}
@keyframes pet-blink {
  0%,
  43%,
  47%,
  92%,
  96%,
  100% {
    transform: scaleY(1);
  }
  45%,
  94% {
    transform: scaleY(0.1);
  }
}
@keyframes pet-jump {
  0% {
    transform: scale(1);
  }
  18% {
    transform: scale(1.12, 0.85) translateY(3px);
  }
  46% {
    transform: scale(0.94, 1.08) translateY(-17px);
  }
  72% {
    transform: scale(1.05, 0.94);
  }
  100% {
    transform: scale(1);
  }
}
@keyframes pet-affection {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.6) rotate(var(--heart-turn));
  }
  25% {
    opacity: 1;
  }
  to {
    opacity: 0;
    transform: translateY(-30px) scale(1.15) rotate(var(--heart-turn));
  }
}
@media (max-width: 960px) {
  .hero-art.pet-habitat {
    height: 294px;
    margin: 0 18px 18px;
    padding: 12px 18px;
  }
  .pet-motion-toggle {
    width: 40px;
    height: 40px;
  }
}
@media (max-width: 600px) {
  .hero-art.pet-habitat {
    margin: 0 12px 12px;
    border-radius: 22px;
  }
  .pet-header {
    min-height: 36px;
  }
  .pet-motion-toggle {
    width: 44px;
    height: 44px;
  }
  .pet-stage {
    height: 154px;
  }
  .pet-touch {
    --pet-scale: 0.94;
  }
  .pet-resume-link {
    min-height: 36px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pet-touch {
    transform: scale(var(--pet-scale, 1));
    transition: none;
  }
  .pet-float,
  .pet-eye,
  .pet-happy .pet-squish,
  .pet-affection span {
    animation: none !important;
  }
  .pet-affection {
    display: none;
  }
}
@supports not (backdrop-filter: blur(1px)) {
  .hero-art.pet-habitat {
    background: #edf5fbed;
  }
}
</style>
