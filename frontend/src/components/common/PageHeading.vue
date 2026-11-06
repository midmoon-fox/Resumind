<script setup lang="ts">
defineProps<{ eyebrow: string; title: string; description?: string }>();
</script>
<template>
  <header class="page-heading">
    <div>
      <h1 class="wrap-heading">{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
    <div class="page-heading-actions"><slot /></div>
  </header>
</template>
