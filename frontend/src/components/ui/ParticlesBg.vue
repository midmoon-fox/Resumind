<!-- Inspired by Inspira UI Particles Background (MIT), adapted for this Vue app without VueUse/Tailwind. -->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';

interface Props {
  color?: string;
  quantity?: number;
  staticity?: number;
  ease?: number;
  class?: string;
}
const props = withDefaults(defineProps<Props>(), {
  quantity: 92,
  staticity: 18,
  ease: 10,
  class: '',
});
interface Particle {
  x: number;
  y: number;
  tx: number;
  ty: number;
  size: number;
  alpha: number;
  targetAlpha: number;
  dx: number;
  dy: number;
  magnetism: number;
}
const canvas = ref<HTMLCanvasElement | null>(null);
let context: CanvasRenderingContext2D | null = null;
let particles: Particle[] = [];
let width = 0;
let height = 0;
let pixelRatio = 1;
let frame = 0;
let mouseX = 0;
let mouseY = 0;
let active = false;
let particleColor = 0;

function rgba(alpha: number) {
  return `rgba(${(particleColor >> 16) & 255}, ${(particleColor >> 8) & 255}, ${particleColor & 255}, ${alpha})`;
}
function createParticle(): Particle {
  return {
    x: Math.random() * width,
    y: Math.random() * height,
    tx: 0,
    ty: 0,
    size: Math.random() * 1.5 + 0.7,
    alpha: 0,
    targetAlpha: Math.random() * 0.45 + 0.12,
    dx: (Math.random() - 0.5) * 0.18,
    dy: (Math.random() - 0.5) * 0.18,
    magnetism: 0.3 + Math.random() * 2.2,
  };
}
function resize() {
  if (!canvas.value || !context) return;
  const color = props.color ?? getComputedStyle(canvas.value).getPropertyValue('--color-accent');
  const hex = color.trim().replace('#', '');
  const expanded = hex.length === 3 ? [...hex].map((c) => c + c).join('') : hex;
  particleColor = Number.parseInt(expanded, 16);
  const rect = canvas.value.getBoundingClientRect();
  width = rect.width;
  height = rect.height;
  pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.value.width = Math.round(width * pixelRatio);
  canvas.value.height = Math.round(height * pixelRatio);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  particles = Array.from({ length: props.quantity }, createParticle);
}
function onPointerMove(event: PointerEvent) {
  if (!canvas.value) return;
  const rect = canvas.value.getBoundingClientRect();
  active =
    event.clientX >= rect.left &&
    event.clientX <= rect.right &&
    event.clientY >= rect.top &&
    event.clientY <= rect.bottom;
  mouseX = event.clientX - rect.left - width / 2;
  mouseY = event.clientY - rect.top - height / 2;
}
function draw() {
  if (!context) return;
  context.clearRect(0, 0, width, height);
  for (const p of particles) {
    const edge = Math.min(p.x, width - p.x, p.y, height - p.y);
    const visibility = Math.min(1, Math.max(0, edge / 20));
    p.alpha += (p.targetAlpha * visibility - p.alpha) * 0.08;
    p.x += p.dx;
    p.y += p.dy;
    const targetX = active ? mouseX / (props.staticity / p.magnetism) : 0;
    const targetY = active ? mouseY / (props.staticity / p.magnetism) : 0;
    p.tx += (targetX - p.tx) / Math.max(1, props.ease);
    p.ty += (targetY - p.ty) / Math.max(1, props.ease);
    if (p.x < -p.size || p.x > width + p.size || p.y < -p.size || p.y > height + p.size)
      Object.assign(p, createParticle());
    context.beginPath();
    context.arc(p.x + p.tx, p.y + p.ty, p.size, 0, Math.PI * 2);
    context.fillStyle = rgba(p.alpha);
    context.fill();
  }
  frame = requestAnimationFrame(draw);
}
onMounted(() => {
  context = canvas.value?.getContext('2d', { alpha: true }) ?? null;
  resize();
  window.addEventListener('resize', resize);
  window.addEventListener('pointermove', onPointerMove, { passive: true });
  frame = requestAnimationFrame(draw);
});
onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
  window.removeEventListener('resize', resize);
  window.removeEventListener('pointermove', onPointerMove);
});
watch(() => [props.quantity, props.color], resize);
</script>

<template>
  <div :class="props.class" aria-hidden="true">
    <canvas ref="canvas" class="particles-canvas" />
  </div>
</template>

<style scoped>
.particles-canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
