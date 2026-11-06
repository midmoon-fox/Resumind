<script setup lang="ts">
import { useRouter } from 'vue-router';
import { ArrowLeft, Sparkles } from '@lucide/vue';
import BaseButton from '../components/common/BaseButton.vue';
const router = useRouter();
</script>
<template>
  <div class="not-found">
    <span class="feature-icon"><Sparkles :size="28" /></span><strong>404</strong>
    <h1 class="wrap-heading">这一站，似乎还没有抵达</h1>
    <p>页面地址可能有误，回到工作台继续探索吧。</p>
    <BaseButton @click="router.push('/dashboard')"><ArrowLeft :size="16" />回到工作台</BaseButton>
  </div>
</template>
