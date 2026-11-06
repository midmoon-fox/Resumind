<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Pause, Play } from '@lucide/vue';
const surface = ref<HTMLDivElement>();
const canvas = ref<HTMLCanvasElement>();
const paused = ref(false);
const inView = ref(true);
let dispose: (() => void) | undefined;
let observer: IntersectionObserver | undefined;
let media: MediaQueryList | undefined;
let generation = 0;
let unmounted = false;
async function configure() {
  const version = ++generation;
  dispose?.();
  dispose = undefined;
  canvas.value?.classList.remove('ribbon-ready');
  if (!media?.matches || !canvas.value || !surface.value || unmounted) return;
  try {
    const { mountRibbon } = await import('./ribbon');
    if (unmounted || version !== generation || !canvas.value || !surface.value) return;
    dispose = mountRibbon(canvas.value, surface.value.parentElement!, () => paused.value);
  } catch {
    /* Static/CSS theme surface remains available without WebGL. */
  }
}
watch(paused, () => {
  surface.value?.parentElement?.dispatchEvent(new Event('ribbon-play'));
  surface.value?.parentElement?.classList.toggle('hero-motion-paused', paused.value);
});
onMounted(() => {
  media = matchMedia('(min-width: 961px) and (prefers-reduced-motion: no-preference)');
  media.addEventListener('change', configure);
  observer = new IntersectionObserver(([entry]) => {
    inView.value = !!entry?.isIntersecting;
    if (inView.value && !dispose) void configure();
  });
  if (surface.value) observer.observe(surface.value);
  document.addEventListener('visibilitychange', visibility);
});
function visibility() {
  inView.value =
    !document.hidden &&
    !!surface.value &&
    surface.value.getBoundingClientRect().bottom > 0 &&
    surface.value.getBoundingClientRect().top < innerHeight;
}
onBeforeUnmount(() => {
  unmounted = true;
  generation++;
  observer?.disconnect();
  media?.removeEventListener('change', configure);
  dispose?.();
  surface.value?.parentElement?.classList.remove('hero-motion-paused');
  document.removeEventListener('visibilitychange', visibility);
});
</script>
<template>
  <div
    ref="surface"
    class="ribbon-backdrop"
    :class="{ 'ribbon-paused': paused || !inView }"
    aria-hidden="true"
  >
    <canvas ref="canvas" class="ribbon-canvas" />
  </div>
  <button
    type="button"
    class="motion-control"
    :aria-pressed="paused"
    :aria-label="paused ? '播放首页背景动效' : '暂停首页背景动效'"
    @click="paused = !paused"
  >
    <Play v-if="paused" :size="13" aria-hidden="true" /><Pause
      v-else
      :size="13"
      aria-hidden="true"
    />
    {{ paused ? '播放动效' : '暂停动效' }}
  </button>
</template>
