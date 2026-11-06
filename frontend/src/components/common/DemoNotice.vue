<script setup lang="ts">
import { useAppStore } from '../../composables/useAppStore';
const { loading, loadError, refreshData, storageStatus, lastSaveError, authWarning } =
  useAppStore();
async function reload() {
  try {
    await refreshData();
  } catch {
    /* shown by loadError */
  }
}
</script>
<template>
  <div class="demo-strip">
    <span>已连接服务端 · JWT 登录</span
    ><small v-if="authWarning" class="storage-error">{{ authWarning }}</small
    ><small v-else-if="loading">正在读取服务端数据…</small
    ><small v-else-if="loadError" class="storage-error" role="alert"
      >{{ loadError }} <button class="text-link" @click="reload">重新加载</button></small
    ><small v-else-if="storageStatus === 'error'" class="storage-error">{{
      lastSaveError || '保存失败，请在编辑器重试'
    }}</small
    ><small v-else>业务数据由服务端保存；收藏及提醒偏好仅本机</small>
  </div>
</template>
