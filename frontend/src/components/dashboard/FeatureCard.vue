<script setup lang="ts">
import { ArrowUpRight, AudioLines, ScanSearch, Sparkles } from '@lucide/vue';
import type { FeatureKey } from '../../types/dashboard';
defineProps<{
  feature: FeatureKey;
  eyebrow: string;
  title: string;
  description: string;
  action: string;
}>();
const emit = defineEmits<{ select: [feature: FeatureKey] }>();
const icons = { generator: Sparkles, jobs: ScanSearch, interview: AudioLines };
</script>

<template>
  <button
    type="button"
    class="feature-card"
    :class="`feature-${feature}`"
    @click="emit('select', feature)"
  >
    <div class="feature-card-top">
      <span class="feature-icon"
        ><component :is="icons[feature]" :size="23" :stroke-width="1.75"
      /></span>
      <h3 class="wrap-heading">{{ title }}</h3>
    </div>
    <p>{{ description }}</p>
    <span class="feature-action">{{ action }}</span
    ><ArrowUpRight class="feature-corner" :size="19" aria-hidden="true" />
  </button>
</template>
