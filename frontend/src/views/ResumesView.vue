<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  Copy,
  Eye,
  FilePlus2,
  History,
  Pencil,
  Plus,
  Trash2,
  SearchX,
  FileText,
} from '@lucide/vue';
import PageHeading from '../components/common/PageHeading.vue';
import BaseButton from '../components/common/BaseButton.vue';
import BaseModal from '../components/common/BaseModal.vue';
import ResumeThumbnail from '../components/dashboard/ResumeThumbnail.vue';
import ResumeDocumentView from '../components/resume/ResumeDocument.vue';
import { useDashboard } from '../composables/useDashboard';
import { useAppStore } from '../composables/useAppStore';
import { useToast } from '../composables/useToast';
import { dateText } from '../utils/content';
import { api } from '../services/client';
import type { Schema } from '../services/schema';
import type { ResumeDocument } from '../types/app';
const router = useRouter();
const { state, createResume, copyResume, deleteResume, restoreVersion } = useAppStore();
const { search, sortOrder, filteredResumes } = useDashboard();
const { success, error } = useToast();
const status = ref('all');
const list = computed(() =>
  filteredResumes.value.filter((r) => status.value === 'all' || r.status === status.value),
);
const preview = ref<ResumeDocument | null>(null);
const pendingDelete = ref<ResumeDocument | null>(null);
const impact = ref<Schema<'DeletionImpact'> | null>(null);
async function requestDelete(resume: ResumeDocument) {
  try {
    impact.value = await api<Schema<'DeletionImpact'>>(`/api/resumes/${resume.id}/deletion-impact`);
    pendingDelete.value = resume;
  } catch (e) {
    error(e instanceof Error ? e.message : '删除预检失败');
  }
}
const historyFor = ref<ResumeDocument | null>(null);
const history = computed(() => state.versions.filter((v) => v.resumeId === historyFor.value?.id));
async function blank() {
  try {
    const doc = await createResume('我的新简历', '');
    await router.push('/resumes/' + doc.id + '/edit');
  } catch (e) {
    error(e instanceof Error ? e.message : '创建失败');
  }
}
async function remove() {
  try {
    if (pendingDelete.value) {
      await deleteResume(pendingDelete.value.id);
      pendingDelete.value = null;
      success('简历及其关联资源已由后端删除。');
    }
  } catch (e) {
    error(e instanceof Error ? e.message : '删除失败');
  }
}
async function copyOne(resume: ResumeDocument) {
  try {
    await copyResume(resume);
    success('已创建独立副本');
  } catch (e) {
    error(e instanceof Error ? e.message : '复制失败');
  }
}
async function restoreOne(id: string) {
  try {
    await restoreVersion(id);
    historyFor.value = null;
    success('已恢复历史版本');
  } catch (e) {
    error(e instanceof Error ? e.message : '恢复失败');
  }
}
</script>
<template>
  <div class="page-container">
    <PageHeading eyebrow="MY RESUMES" title="我的简历" description=""
      ><BaseButton variant="secondary" @click="blank"><FilePlus2 :size="17" />空白简历</BaseButton
      ><BaseButton @click="router.push('/create')"
        ><Plus :size="17" />AI 制作简历</BaseButton
      ></PageHeading
    >
    <div class="stat-grid">
      <div class="stat-card">
        <span>全部简历</span><strong>{{ state.resumes.length }}<small>份成长记录</small></strong>
      </div>
      <div class="stat-card">
        <span>已完成</span
        ><strong
          >{{ state.resumes.filter((r) => r.status === 'ready').length
          }}<small>份准备就绪</small></strong
        >
      </div>
      <div class="stat-card">
        <span>历史版本</span><strong>{{ state.versions.length }}<small>个保留节点</small></strong>
      </div>
    </div>
    <div class="panel">
      <div class="list-toolbar">
        <div class="tabs" aria-label="简历筛选">
          <button
            v-for="tab in [
              { id: 'all', name: '全部简历' },
              { id: 'draft', name: '草稿' },
              { id: 'ready', name: '资料完整' },
            ]"
            :key="tab.id"
            :class="{ active: status === tab.id }"
            @click="status = tab.id"
          >
            {{ tab.name }}
          </button>
        </div>
        <div class="toolbar-fields">
          <ElInput
            v-model="search"
            aria-label="搜索我的简历"
            placeholder="搜索简历名称或方向"
            type="search"
          /><ElSelect v-model="sortOrder" aria-label="排序简历"
            ><ElOption value="updated" :label="'最近更新'" />
            <ElOption value="name" :label="'名称排序'"
          /></ElSelect>
        </div>
      </div>
      <div v-if="list.length" class="library-grid">
        <article v-for="resume in list" :key="resume.id" class="library-card">
          <button
            class="library-preview"
            :aria-label="'预览' + resume.title"
            @click="preview = resume"
          >
            <ResumeThumbnail :variant="resume.template" /><span
              class="resume-status"
              :class="'status-' + resume.status"
              >{{ resume.status === 'ready' ? '资料完整' : '草稿' }}</span
            >
          </button>
          <div class="library-card-body">
            <h2 class="wrap-heading">{{ resume.title }}</h2>
            <p>{{ resume.role }} / {{ dateText(resume.updatedAt) }}</p>
            <div class="completion-row"><span :style="{ width: resume.completeness + '%' }" /></div>
            <small>完整度 {{ resume.completeness }}%</small>
            <div class="card-actions">
              <BaseButton size="small" @click="router.push('/resumes/' + resume.id + '/edit')"
                ><Pencil :size="14" />继续编辑</BaseButton
              ><button
                class="icon-button"
                :aria-label="'预览详情' + resume.title"
                @click="preview = resume"
              >
                <Eye :size="16" /></button
              ><button
                class="icon-button"
                :aria-label="'复制' + resume.title"
                @click="copyOne(resume)"
              >
                <Copy :size="16" /></button
              ><button
                class="icon-button"
                :aria-label="'历史版本' + resume.title"
                @click="historyFor = resume"
              >
                <History :size="16" /></button
              ><button
                class="icon-button danger-icon"
                :aria-label="'删除' + resume.title"
                @click="requestDelete(resume)"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="app-empty">
        <SearchX :size="34" />
        <h2 class="wrap-heading">
          {{ state.resumes.length ? '没有找到匹配的简历' : '还没有简历' }}
        </h2>
        <p>试试其他关键词，或者从第一份简历开始。</p>
        <BaseButton
          variant="secondary"
          @click="
            search = '';
            status = 'all';
          "
          >清空筛选</BaseButton
        >
      </div>
    </div>
    <BaseModal :open="!!preview" :title="preview?.title || '简历预览'" wide @close="preview = null"
      ><div v-if="preview" class="document-modal-preview">
        <ResumeDocumentView :document="preview" />
      </div>
      <BaseButton
        v-if="preview"
        class="full-width"
        @click="router.push('/resumes/' + preview.id + '/edit')"
        >编辑这份简历 <Pencil :size="16" /></BaseButton
    ></BaseModal>
    <BaseModal :open="!!pendingDelete" title="删除这份简历？" @close="pendingDelete = null"
      ><p class="body-copy">
        将删除「{{ pendingDelete?.title }}」及其
        {{ state.versions.filter((v) => v.resumeId === pendingDelete?.id).length }}
        个历史版本。关联面试准备与导出资源也会受影响，具体范围以服务端删除预检为准。
      </p>
      <p v-for="message in impact?.messages" :key="message">{{ message }}</p>
      <p v-if="impact">关联数量：{{ impact.affectedCounts }}</p>
      <div class="modal-actions">
        <BaseButton variant="secondary" @click="pendingDelete = null">取消</BaseButton
        ><BaseButton class="danger-button" @click="remove">确认删除</BaseButton>
      </div></BaseModal
    >
    <BaseModal :open="!!historyFor" title="历史版本" @close="historyFor = null"
      ><div v-if="!history.length" class="app-empty compact">
        <FileText :size="28" />
        <p>还没有版本。在编辑器中点击“保存版本”即可创建。</p>
      </div>
      <div v-for="version in history" :key="version.id" class="history-row">
        <div>
          <strong>{{ version.label }}</strong
          ><small>{{ dateText(version.createdAt) }} / 修订 {{ version.document.revision }}</small>
        </div>
        <BaseButton size="small" variant="secondary" @click="restoreOne(version.id)"
          >恢复</BaseButton
        >
      </div></BaseModal
    >
  </div>
</template>

<style scoped>
/* Hallmark · shape: app screen · genre: modern-minimal · theme: brand · redesign: full · v2.0.0 */
/* Hallmark · pre-emit critique: P4 H5 E4 S4 R5 V3 · weakest: V, kept shared workspace shell */
.wrap-heading {
  overflow-wrap: break-word;
  min-width: 0;
  text-wrap: balance;
}
</style>

<style scoped>
.document-modal-preview {
  height: min(68dvh, 860px);
  min-height: 280px;
  overflow: hidden;
}
.document-modal-preview :deep(.server-resume-preview) {
  height: 100%;
}
</style>
<style>
.el-dialog:has(.document-modal-preview) {
  margin-top: 4dvh;
  margin-bottom: 4dvh;
}
</style>
