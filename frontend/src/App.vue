<script setup lang="ts">
import gsap from 'gsap';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import { RouterView } from 'vue-router';
import AppLayout from './layouts/AppLayout.vue';

function enterRoute(element: Element, done: () => void) {
  gsap.fromTo(
    element,
    { autoAlpha: 0, y: 18, scale: 0.99, filter: 'blur(8px)' },
    {
      autoAlpha: 1,
      y: 0,
      scale: 1,
      filter: 'blur(0px)',
      duration: 0.68,
      ease: 'power3.out',
      clearProps: 'all',
      onComplete: done,
    },
  );
}

function leaveRoute(element: Element, done: () => void) {
  gsap.to(element, {
    autoAlpha: 0,
    y: -6,
    filter: 'blur(3px)',
    duration: 0.18,
    ease: 'power2.in',
    onComplete: done,
  });
}
</script>

<template>
  <ElConfigProvider :locale="zhCn" :z-index="3000" :empty-values="[null, undefined]"
    ><AppLayout>
      <RouterView v-slot="{ Component, route }">
        <Transition :css="false" mode="out-in" @enter="enterRoute" @leave="leaveRoute">
          <div :key="route.path" class="route-surface"><component :is="Component" /></div>
        </Transition>
      </RouterView> </AppLayout
  ></ElConfigProvider>
</template>

<style scoped>
/* Hallmark · shape: app screen · genre: modern-minimal · theme: brand · redesign: full · v2.0.0 */
/* Hallmark · pre-emit critique: P4 H5 E4 S4 R5 V3 · weakest: V, kept shared workspace shell */
.app-shell {
  min-width: 0;
}
</style>
