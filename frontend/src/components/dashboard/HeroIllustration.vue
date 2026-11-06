<script setup lang="ts">
import { computed } from 'vue';
import ResumeDocumentView from '../resume/ResumeDocument.vue';
import { useAppStore } from '../../composables/useAppStore';
const { state } = useAppStore();
const recent = computed(
  () => [...state.resumes].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt))[0],
);
</script>
<template>
  <div class="hero-art" aria-hidden="true">
    <p class="hero-art-label">最近编辑的简历</p>
    <ResumeDocumentView v-if="recent" :document="recent" />
    <div v-else class="hero-art-empty">你的简历将在这里呈现</div>
  </div>
</template>

<style scoped>
/* Hallmark · shape: app screen · genre: modern-minimal · theme: brand · redesign: full · v2.0.0 */
/* Hallmark · pre-emit critique: P4 H5 E4 S4 R5 V3 · weakest: V, kept shared workspace shell */
.hero-art {
  min-width: 0;
}
</style>
