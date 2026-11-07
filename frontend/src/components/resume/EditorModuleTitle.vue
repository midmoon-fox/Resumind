<script setup lang="ts">
import { computed } from 'vue';
import type { Component } from 'vue';
import {
  Trash2,
  UserRound,
  GraduationCap,
  Wrench,
  Briefcase,
  BriefcaseBusiness,
  School,
  Trophy,
  Award,
  Target,
  BarChart3,
  Heart,
  BookOpen,
  Users,
  Link,
  Star,
  FileText,
  HandHeart,
} from '@lucide/vue';
const props = withDefaults(defineProps<{ title: string; anchor: string; expanded: boolean; removable?: boolean }>(), {
  removable: true,
});
defineEmits<{ remove: [] }>();
const ICONS: Record<string, Component> = {
  基本信息: UserRound,
  教育经历: GraduationCap,
  专业技能: Wrench,
  项目经历: Briefcase,
  实习经历: BriefcaseBusiness,
  校园经历: School,
  获奖经历: Trophy,
  成就: Award,
  证书: FileText,
  目标: Target,
  图表: BarChart3,
  爱好: Heart,
  发表作品: BookOpen,
  推荐人: Users,
  社交媒体: Link,
  优势: Star,
  文本: FileText,
  志愿服务: HandHeart,
  工作经验: Briefcase,
};
const icon = computed(() => ICONS[props.title] ?? FileText);
</script>
<template>
  <span class="module-title-row">
    <span class="module-title-icon" aria-hidden="true"><component :is="icon" :size="17" /></span>
    <span class="editor-card-title" :id="anchor">{{ title }}</span>
    <button v-if="expanded && removable !== false" type="button" class="module-title-delete"
      :aria-label="'删除模块' + title" :title="'删除' + title"
      @click.stop="$emit('remove')" @keydown.stop>
      <Trash2 :size="17" />
    </button>
  </span>
</template>
<style scoped>
.module-title-row { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.module-title-icon { flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center;
  color: var(--el-color-primary); }
.editor-card-title { flex: 1; min-width: 0; }
.module-title-delete { flex: 0 0 30px; width: 30px; height: 30px; display: inline-flex;
  align-items: center; justify-content: center; border: 0; background: transparent;
  color: #dc2626; border-radius: 6px; cursor: pointer; margin-right: 8px; }
.module-title-delete:hover { background: #fef2f2; }
.module-title-delete:focus-visible { outline: 2px solid #dc2626; outline-offset: 2px; }
</style>
