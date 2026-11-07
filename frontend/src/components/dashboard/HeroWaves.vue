<script setup lang="ts">
import { createNoise3D } from 'simplex-noise';
import { onBeforeUnmount, onMounted, ref } from 'vue';

const canvasRef = ref<HTMLCanvasElement | null>(null);
let dispose: (() => void) | undefined;

onMounted(() => {
  const canvas = canvasRef.value;
  const context = canvas?.getContext('2d');
  if (!canvas || !context) return;

  // Layered simplex-noise waves follow the Inspira UI Wavy Background effect.
  const noise = createNoise3D();
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const start = performance.now();
  let frame = 0;
  let width = 0;
  let height = 0;
  let gradient: CanvasGradient;

  const draw = (time: number) => {
    if (!width || !height) return;
    context.clearRect(0, 0, width, height);
    context.fillStyle = gradient;
    const amplitude = Math.min(height * 0.23, 82);
    const maxHalfWidth = Math.min(74, Math.max(36, height * 0.18)) / 2;
    const steps = Math.ceil(width / 8);
    for (let wave = 0; wave < 2; wave++) {
      const baseline = height * (0.385 + wave * 0.23);
      const waveY = (x: number) => baseline + noise(x / 680, wave * 0.36, time * 0.16) * amplitude;
      const halfWidth = (position: number) => maxHalfWidth * Math.sqrt(Math.sin(Math.PI * position));
      context.beginPath();
      context.moveTo(0, waveY(0));
      for (let step = 1; step <= steps; step++) {
        const position = step / steps;
        const x = width * position;
        context.lineTo(x, waveY(x) - halfWidth(position));
      }
      for (let step = steps - 1; step >= 0; step--) {
        const position = step / steps;
        const x = width * position;
        context.lineTo(x, waveY(x) + halfWidth(position));
      }
      context.closePath();
      context.fill();
    }
  };

  const resize = () => {
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    if (!width || !height) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    gradient = context.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, '#4CC9F000');
    gradient.addColorStop(0.42, '#4CC9F0');
    gradient.addColorStop(0.58, '#4CC9F0');
    gradient.addColorStop(1, '#4CC9F000');
    draw(motion.matches ? 0 : (performance.now() - start) / 1000);
  };

  const animate = (time: number) => {
    draw((time - start) / 1000);
    frame = requestAnimationFrame(animate);
  };

  const updateMotion = () => {
    cancelAnimationFrame(frame);
    if (motion.matches) draw(0);
    else frame = requestAnimationFrame(animate);
  };

  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  resize();
  updateMotion();
  motion.addEventListener('change', updateMotion);
  dispose = () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    motion.removeEventListener('change', updateMotion);
  };
});

onBeforeUnmount(() => dispose?.());
</script>

<template>
  <canvas ref="canvasRef" class="hero-waves" aria-hidden="true"></canvas>
</template>

<style scoped>
.hero-waves {
  position: absolute;
  z-index: 0;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.32;
  filter: blur(16px);
  mask-image: linear-gradient(transparent, #000 14%, #000 86%, transparent);
  pointer-events: none;
}
</style>
