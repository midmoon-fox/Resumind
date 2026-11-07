<script setup lang="ts">
import { computed, ref } from 'vue';
import { Check } from '@lucide/vue';
import { resumeTemplates, type ResumeTemplateId } from '../../types/templates';
defineProps<{ modelValue: ResumeTemplateId; disabled?: boolean }>();
const emit = defineEmits<{ 'update:modelValue': [value: ResumeTemplateId] }>();
const category = ref('全部模板');
const categories = computed(() => ['全部模板', ...new Set(resumeTemplates.map((t) => t.category))]);
const templates = computed(() =>
  resumeTemplates.filter((t) => category.value === '全部模板' || t.category === category.value),
);
</script>
<template>
  <section class="template-showcase" aria-label="简历模板选择">
    <header class="showcase-heading">
      <h1>简历模板</h1>
    </header>
    <div class="showcase-filters" role="group" aria-label="模板分类">
      <button
        v-for="name in categories"
        :key="name"
        type="button"
        :class="{ active: category === name }"
        :aria-pressed="category === name"
        @click="category = name"
      >
        {{ name }}
      </button>
    </div>
    <div class="showcase-grid">
      <button
        v-for="template in templates"
        :key="template.id"
        type="button"
        class="showcase-card"
        :class="{ selected: modelValue === template.id }"
        :aria-pressed="modelValue === template.id"
        :aria-label="'选择' + template.title"
        :disabled="disabled"
        @click="emit('update:modelValue', template.id)"
      >
        <div class="showcase-paper" :class="'paper-' + template.id" aria-hidden="true">
          <header class="paper-heading">
            <small>个人简历</small><strong>林同学</strong><span>前端开发工程师</span>
            <p>138 0000 0000　·　lin@example.com</p>
          </header>
          <section>
            <h3>教育经历</h3>
            <h4>示例大学 <span>2021.09 — 2025.06</span></h4>
            <p>计算机科学与技术 / 本科</p>
          </section>
          <section>
            <h3>项目经历</h3>
            <h4>校园服务平台 <span>前端开发</span></h4>
            <p>负责页面开发与组件整理，完善表单交互和移动端适配。</p>
            <p>与团队协作完成需求梳理、功能测试及项目展示。</p>
            <h4>个人作品集</h4>
            <p>整理项目过程与设计思考，清晰展示实际贡献。</p>
          </section>
          <section>
            <h3>实习经历</h3>
            <h4>前端开发实习生</h4>
            <p>参与业务页面维护，梳理组件使用规范，配合完成联调与测试。</p>
          </section>
          <section>
            <h3>专业技能</h3>
            <p>Vue · TypeScript · JavaScript · HTML · CSS</p>
            <p>掌握常用开发工具，注重界面细节与协作沟通。</p>
          </section>
          <section>
            <h3>校园经历</h3>
            <h4>技术社团 · 项目成员</h4>
            <p>参与校园活动筹备，协助完成技术交流与作品展示。</p>
          </section>
        </div>
        <footer class="showcase-card-footer">
          <span>{{ template.title }}</span
          ><span v-if="modelValue === template.id" class="showcase-selected"
            ><Check :size="14" />已选择</span
          ><span v-else class="showcase-category">{{ template.category }}</span>
        </footer>
      </button>
    </div>
    <p class="showcase-note">以上为版式示意，生成时会使用你填写的真实资料。</p>
  </section>
</template>
<style scoped>
.template-showcase {
  max-width: 1320px;
  margin: 0 auto;
  padding: 28px 0 20px;
}
.showcase-heading {
  text-align: center;
  margin-bottom: 28px;
}
.showcase-heading h1 {
  font-size: clamp(30px, 4vw, 42px);
  font-weight: 700;
  letter-spacing: 0.04em;
  margin: 0 0 12px;
  color: var(--color-ink);
}
.showcase-heading p {
  font-size: 14px;
  color: var(--color-muted);
  margin: 0;
}
.showcase-filters {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 42px;
}
.showcase-filters button {
  border: 1px solid var(--color-rule);
  border-radius: 9px;
  padding: 9px 18px;
  background: #fff;
  color: var(--color-ink-2);
  cursor: pointer;
}
.showcase-filters button.active {
  background: var(--color-accent);
  color: var(--color-accent-ink);
  border-color: var(--color-accent);
}
.showcase-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 320px));
  justify-content: center;
  gap: 24px;
}
.showcase-card {
  padding: 0;
  min-width: 0;
  overflow: hidden;
  text-align: left;
  background: white;
  border: 1px solid var(--color-rule);
  border-radius: 12px;
  cursor: pointer;
  box-shadow: 0 2px 8px var(--color-shadow-soft);
  transition:
    transform 0.2s,
    box-shadow 0.2s,
    border-color 0.2s;
}
.showcase-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 14px 32px var(--color-shadow-raised);
}
.showcase-card.selected {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px var(--color-focus-soft);
}
.showcase-card:focus-visible,
.showcase-filters button:focus-visible {
  outline: 3px solid var(--color-focus);
  outline-offset: 4px;
}
.showcase-paper {
  aspect-ratio: 210/297;
  padding: 26px 22px;
  background: #fff;
  color: #30343d;
  font-family: 'Microsoft YaHei', sans-serif;
  overflow: hidden;
}
.paper-heading {
  padding: 0 0 12px;
  margin-bottom: 14px;
}
.paper-heading small {
  display: block;
  letter-spacing: 3px;
  color: #9b96a3;
  font-size: 7px;
  margin-bottom: 5px;
}
.paper-heading strong {
  display: block;
  font-size: 23px;
  line-height: 1.3;
}
.paper-heading span {
  display: block;
  font-size: 9px;
  margin: 5px 0;
}
.showcase-paper p {
  font-size: 7px;
  line-height: 1.75;
  margin: 3px 0;
}
.showcase-paper section {
  margin-top: 12px;
}
.showcase-paper h3 {
  font-size: 10px;
  margin: 0 0 7px;
  padding-bottom: 4px;
  border-bottom: 1px solid #aaaab1;
}
.showcase-paper h4 {
  font-size: 8px;
  margin: 6px 0 3px;
  display: flex;
  justify-content: space-between;
  gap: 4px;
}
.showcase-paper h4 span {
  font-size: 6px;
  font-weight: 400;
  color: #7d7785;
}
.paper-project .paper-heading {
  border-left: 4px solid #7763b6;
  padding-left: 12px;
}
.paper-project h3 {
  color: #7763b6;
  border-bottom-color: #c9bde5;
}
.paper-project {
  background: linear-gradient(180deg, #faf9fd, white 38%);
}
.paper-ribbon { padding-top: 52px; position: relative; }
.paper-ribbon::before { content: '个人简历'; position: absolute; top: 16px; left: 22px; color: #aaa3be; font-size: 22px; letter-spacing: 4px; }
.paper-ribbon::after { content: ''; position: absolute; left: 0; right: 0; top: 46px; height: 6px; background: linear-gradient(60deg, #aaa3be 60%, #e8e5ed 60%); }
.paper-ribbon .paper-heading { padding-top: 10px; }
.paper-ribbon .paper-heading small { display: none; }
.paper-ribbon section { border-left: 1px solid #d5d0dd; padding-left: 8px; }
.paper-ribbon h3 { position: relative; margin-left: -13px; padding: 1px 12px 2px 7px; color: white; border: 0; background: linear-gradient(48deg, #aaa3be 42%, #e8e5ed 42%, #e8e5ed 44%, transparent 44%); }
.paper-sidebar { display: grid; grid-template-columns: 30% minmax(0, 1fr); column-gap: 10px; padding: 28px 12px 12px 0; position: relative; background: linear-gradient(to right, #f0f1f2 0 30%, white 30%); border-bottom: 6px solid #879fb7; }
.paper-sidebar::before { content: '● ● · ·'; color: white; letter-spacing: 3px; position: absolute; top: 0; left: 0; right: 0; height: 20px; padding-left: 10px; background: #879fb7; font-size: 12px; }
.paper-sidebar .paper-heading { grid-column: 1; grid-row: 1 / span 6; padding: 0 7px; margin-top: 10px; text-align: center; }
.paper-sidebar .paper-heading::before { content: ''; display: block; width: 40px; height: 54px; margin: 0 auto 12px; background: linear-gradient(#d5dce2, #e4e8eb); border: 2px solid white; }
.paper-sidebar .paper-heading small { display: none; }
.paper-sidebar .paper-heading strong { font-size: 15px; }
.paper-sidebar .paper-heading span { font-size: 7px; }
.paper-sidebar .paper-heading p { overflow-wrap: anywhere; font-size: 6px; }
.paper-sidebar section { grid-column: 2; margin-top: 5px; }
.paper-sidebar h3 { color: #657e95; border-color: #d5d9dd; }
.paper-sidebar h3::before { content: ''; display: inline-block; width: 6px; height: 6px; background: #879fb7; border-radius: 50%; margin-right: 4px; }
.paper-sidebar h4 { display: block; }
.paper-sidebar h4 span { display: block; }
.showcase-card-footer {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
  padding: 13px 14px;
  background: var(--color-canvas);
  border-top: 1px solid var(--color-rule);
  font-size: 13px;
  font-weight: 600;
}
.showcase-selected {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--color-accent);
  font-size: 11px;
}
.showcase-category {
  font-size: 10px;
  color: var(--color-muted);
  font-weight: 400;
}
.showcase-note {
  text-align: center;
  color: var(--color-muted);
  font-size: 12px;
  margin: 26px 0 0;
}
@media (max-width: 600px) {
  .showcase-grid {
    grid-template-columns: minmax(0, 340px);
    gap: 20px;
  }
  .template-showcase {
    padding-top: 12px;
  }
  .showcase-filters {
    margin-bottom: 26px;
  }
  .showcase-paper:not(.paper-sidebar) {
    padding: 30px 25px;
  }
  .showcase-paper p {
    font-size: 8px;
  }
  .showcase-paper h3 {
    font-size: 11px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .showcase-card {
    transition: none;
  }
  .showcase-card:hover {
    transform: none;
  }
}
</style>

<style scoped>
.template-showcase > .showcase-heading { display:block; width:100%; max-width:none; text-align:center; }
.template-showcase .showcase-heading h1, .template-showcase .showcase-heading p { width:100%; max-width:none; margin-inline:auto; text-align:center; }
.showcase-paper section { margin-top:8px; }
.showcase-paper .paper-heading { padding-bottom:8px; margin-bottom:8px; }
.showcase-paper h3 { margin-bottom:5px; }
</style>
