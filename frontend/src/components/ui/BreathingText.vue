<!-- Inspired by Inspira UI Breathing Text (MIT); CSS animation keeps the staggered variable-axis effect without Motion-V. -->
<script setup lang="ts">
import { computed } from 'vue';
const props = withDefaults(defineProps<{ text: string; class?: string; staggerDuration?: number }>(), { staggerDuration: .075, class: '' });
const letters = computed(() => [...props.text]);
</script>

<template>
  <h1 :class="['breathing-text', props.class]" :aria-label="props.text">
    <span v-for="(letter, index) in letters" :key="`${index}-${letter}`" class="breathing-letter" aria-hidden="true" :style="{ '--delay': `${index * props.staggerDuration}s` }">{{ letter === ' ' ? '\u00a0' : letter }}</span>
  </h1>
</template>

<style scoped>
.breathing-text { margin: 0; }
.breathing-letter { display: inline-block; transform-origin: 50% 70%; animation: breathe 2.8s ease-in-out var(--delay) infinite alternate; }
@keyframes breathe {
  0%, 100% { font-variation-settings: 'wght' 620, 'wdth' 92; font-weight: 650; transform: translateY(0) scaleX(.99); }
  55% { font-variation-settings: 'wght' 780, 'wdth' 112; font-weight: 800; transform: translateY(-2px) scaleX(1.015); }
}
@media (prefers-reduced-motion: reduce) { .breathing-letter { animation: none; } }
</style>
