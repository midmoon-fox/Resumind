<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { Save, Upload, UserRound } from '@lucide/vue';
import FileUpload from '../components/common/FileUpload.vue';
import PageHeading from '../components/common/PageHeading.vue';
import BaseButton from '../components/common/BaseButton.vue';
import { useAppStore } from '../composables/useAppStore';
import { api, uploadFile } from '../services/client';
import type { Schema } from '../services/schema';
const { state, user, persist, refreshAccount, logout } = useAppStore();
const router = useRouter();
const nickname = ref(state.account.nickname),
  selectedAvatar = ref<File | null>(null),
  removeAvatar = ref(false),
  busy = ref(false),
  error = ref(''),
  success = ref('');
async function save() {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  success.value = '';
  try {
    if (!nickname.value.trim()) throw new Error('请填写昵称');
    const input: Schema<'MePatch'> = { username: nickname.value.trim() };
    if (
      selectedAvatar.value &&
      (!['image/png', 'image/jpeg'].includes(selectedAvatar.value.type) ||
        selectedAvatar.value.size > 2 * 1024 * 1024)
    )
      throw new Error('请选择 2MB 以内的 PNG / JPG 头像');
    if (selectedAvatar.value)
      input.avatarFileId = (await uploadFile(selectedAvatar.value, 'AVATAR')).id;
    else if (removeAvatar.value) input.avatarFileId = null;
    await api('/api/me', 'PATCH', input);
    await refreshAccount();
    persist();
    selectedAvatar.value = null;
    success.value = '昵称和头像已保存到服务端；城市、求职方向与提醒偏好仅保存在本机。';
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败';
  } finally {
    busy.value = false;
  }
}
async function signout() {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    await logout();
    await router.replace('/login');
  } catch (e) {
    error.value = e instanceof Error ? e.message : '退出失败，请重试';
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="page-container">
    <PageHeading
      eyebrow="YOUR PERSONAL SPACE"
      title="个人中心"
      description="用户信息"
    />
    <div class="profile-grid">
      <aside class="panel profile-summary">
        <div class="profile-avatar">
          <img v-if="state.account.avatar" :src="state.account.avatar" alt="当前头像" /><UserRound
            v-else
            :size="44"
          />
        </div>
        <h2>{{ state.account.nickname }}</h2>
        <p>{{ user?.email }}</p>
        <p>{{ state.resumes.length }} 份简历</p>
        <BaseButton variant="secondary" :loading="busy" @click="signout">退出登录</BaseButton>
      </aside>
      <div class="profile-panels">
        <section class="panel">
          <h2>账户资料</h2>
          <form @submit.prevent="save">
            <label class="field"
              >昵称<ElInput v-model="nickname" required maxlength="50" aria-label="昵称" /></label
            ><label class="field"
              >头像（PNG / JPG，2MB 以内）<FileUpload
                accept="image/png,image/jpeg"
                @select="(files) => (selectedAvatar = files[0] ?? null)" /></label
            ><ElCheckbox class="check-label" v-model="removeAvatar">移除现有头像</ElCheckbox>
            <p v-if="selectedAvatar"><Upload :size="14" />{{ selectedAvatar.name }}</p>
            <p v-if="error" class="form-error" role="alert">{{ error }}</p>
            <p v-if="success" role="status">{{ success }}</p>
            <div class="inline-actions">
              <BaseButton type="submit" :loading="busy"><Save :size="16" />保存账户资料</BaseButton>
            </div>
          </form>
        </section>
        <!-- <section class="panel">
          <h2>本机偏好</h2>
          <p class="body-copy">以下设置只保存在当前浏览器，不会修改简历内容或发送提醒。</p>
          <label class="field"
            >账户城市<ElInput
              v-model="state.account.city"
              maxlength="50"
              aria-label="账户城市" /></label
          ><label class="field"
            >求职方向<ElInput
              v-model="state.account.direction"
              maxlength="100"
              aria-label="求职方向"
          /></label>
          <div class="setting-row">
            <span>简历更新提醒偏好（本机）</span
            ><ElSwitch v-model="state.notifications.saveReminder" />
          </div>
          <div class="setting-row">
            <span>面试准备提醒偏好（本机）</span
            ><ElSwitch v-model="state.notifications.interviewReminder" />
          </div>
          <BaseButton variant="secondary" @click="persist">保存本机设置</BaseButton>
        </section>
        <section class="panel">
          <h2>资料导出</h2>
          <p>导出当前已加载的简历和 JD JSON。备份可能含个人资料，请妥善保存。</p>
          <BaseButton variant="secondary" @click="backup"
            ><Download :size="16" />导出 JSON 备份</BaseButton
          >
        </section> -->
      </div>
    </div>
  </div>
</template>
