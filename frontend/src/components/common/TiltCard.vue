<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import VanillaTilt from 'vanilla-tilt';

const surface = ref<HTMLDivElement | null>(null);
let tilt: VanillaTilt | undefined;
let motionQuery: MediaQueryList | undefined;

function destroyTilt() {
  tilt?.destroy();
  tilt = undefined;
  // The library resets glare opacity but leaves its generated nodes in the DOM.
  surface.value?.querySelectorAll(':scope > .js-tilt-glare').forEach((node) => node.remove());
}

function updateTilt() {
  destroyTilt();
  if (!surface.value || !motionQuery?.matches) return;
  tilt = new VanillaTilt(surface.value, {
    max: 6,
    perspective: 1200,
    speed: 450,
    scale: 1,
    glare: true,
    'max-glare': 0.14,
    gyroscope: false,
  });
}

onMounted(() => {
  motionQuery = window.matchMedia(
    '(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)',
  );
  motionQuery.addEventListener('change', updateTilt);
  updateTilt();
});
onBeforeUnmount(() => {
  motionQuery?.removeEventListener('change', updateTilt);
  destroyTilt();
});
</script>

<template>
  <div ref="surface" class="tilt-surface"><slot /></div>
</template>

<style scoped>
.tilt-surface {
  transform-style: preserve-3d;
}
.tilt-surface > :deep(.js-tilt-glare) {
  border-radius: inherit;
  pointer-events: none;
}
</style>
