<script setup lang="ts">
import ProfilePhoto from '../components/resume/ProfilePhoto.vue';
import { computed, ref, watch, nextTick } from 'vue';
import { validateCreateStep } from '../services/createValidation';
import { useRouter, onBeforeRouteLeave } from 'vue-router';
import {
  ArrowLeft,
  ArrowRight,
  FileText,
  Plus,
  Sparkles,
  Trash2,
  Upload,
  Merge,
} from '@lucide/vue';
import FileUpload from '../components/common/FileUpload.vue';
import JdEditor from '../components/jd/JdEditor.vue';
import PageHeading from '../components/common/PageHeading.vue';
import AdditionalEducation from '../components/resume/AdditionalEducation.vue';
import EducationDates from '../components/resume/EducationDates.vue';
import BaseButton from '../components/common/BaseButton.vue';
import BaseModal from '../components/common/BaseModal.vue';
import TemplateGallery from '../components/resume/TemplateGallery.vue';
import type { ResumeTemplateId } from '../types/templates';
import MaterialDetails from '../components/resume/MaterialDetails.vue';
import FollowupPanel from '../components/resume/FollowupPanel.vue';
import { useAppStore, exampleProfile } from '../composables/useAppStore';
import { useToast } from '../composables/useToast';
import { api, uploadFile } from '../services/client';
import { archiveTitle } from '../services/jd';
import { waitTask, resource, tasks } from '../services/tasks';
import type { Schema } from '../services/schema';
import { experienceData, mergeSources } from '../services/mapping';

const router = useRouter();
const { state, saveWorkspace, saveExperiences, refreshWorkspace, refreshResume, refreshData } =
  useAppStore();
const { notify, success } = useToast();
const draft = computed(() => state.workspace);
const fieldErrors = ref<Record<string, string>>({});
watch(
  () => [
    draft.value.title,
    draft.value.direction,
    draft.value.profile.name,
    draft.value.profile.email,
    draft.value.profile.phone,
  ],
  () => {
    const current = validateCreateStep(draft.value.step, draft.value);
    for (const key of Object.keys(fieldErrors.value))
      if (!current[key]) delete fieldErrors.value[key];
  },
);
async function validateCurrentStep() {
  fieldErrors.value = validateCreateStep(draft.value.step, draft.value);
  if (!Object.keys(fieldErrors.value).length) return true;
  await nextTick();
  const field = document.querySelector<HTMLElement>('.wizard-panel [aria-invalid="true"]');
  field?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  (field?.matches('input,textarea')
    ? field
    : field?.querySelector<HTMLElement>('input,textarea')
  )?.focus();
  return false;
}

const steps = ['目标岗位', '基本资料', '经历材料', '补充追问'];
const jdDraft = ref<{ text: string; file: File | null }>({ text: '', file: null });
const hasJdDraft = computed(() => !!jdDraft.value.text.trim() || !!jdDraft.value.file);
async function submitJdDraft() {
  if (!hasJdDraft.value) return;
  const file = jdDraft.value.file ? await uploadFile(jdDraft.value.file, 'JD') : null;
  const accepted = await api<Schema<'AsyncAccepted'>>('/api/job-descriptions', 'POST', {
    title: archiveTitle(draft.value.direction),
    ...(file ? { fileId: file.id } : {}),
    ...(jdDraft.value.text.trim() ? { text: jdDraft.value.text.trim() } : {}),
  });
  const version = await resource<Schema<'JdVersionOut'>>(accepted);
  const jd = await api<Schema<'JdOut'>>(`/api/job-descriptions/${version.jdId}`);
  await api(`/api/job-descriptions/${jd.id}/confirmations`, 'POST', {
    baseRevision: jd.revision,
    jdVersionId: version.id,
    title: jd.title,
    originalText: version.originalText,
    jobTitle: version.jobTitle,
    companyName: version.companyName,
    requirements: version.requirements,
  });
  await refreshData();
  draft.value.jdId = jd.id;
  jdDraft.value = { text: '', file: null };
}
function selectExperience(id: string, checked: boolean) {
  selected.value = checked
    ? [...new Set([...selected.value, id])]
    : selected.value.filter((value) => value !== id);
}
const selected = ref<string[]>([]),
  busy = ref(false),
  error = ref('');
const jdEditorOpen = ref(false),
  jdBusy = ref(false),
  jdEditorKey = ref(0);
async function jdSaved(id: string) {
  draft.value.jdId = id;
  jdEditorOpen.value = false;
  await run(async () => {
    await saveWorkspace('JD');
    jdEditorKey.value++;
    success('岗位 JD 已保存并关联到当前简历');
  });
}
const followupBusy = ref(false);
async function followupCompleted() {
  await run(async () => {
    await saveWorkspace('EDITOR');
    draft.value.step = 4;
  });
}
const generationTaskId = ref('');
const generationTask = computed(() => tasks.find((t) => t.id === generationTaskId.value));
const generationStatus = computed(() =>
  generationTask.value
    ? {
        QUEUED: '正在排队',
        RUNNING: 'AI 正在生成简历内容',
        SUCCEEDED: '生成完成，正在打开编辑页',
        FAILED: '生成失败，请查看错误或后台任务',
        CANCEL_REQUESTED: '正在取消',
        CANCELLED: '任务已取消',
      }[generationTask.value.status]
    : '正在提交生成请求',
);
async function run(action: () => Promise<void>) {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    await action();
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败';
  } finally {
    busy.value = false;
  }
}
async function next() {
  if (jdBusy.value || followupBusy.value) return;
  if (!(await validateCurrentStep())) return;
  await run(async () => {
    if (draft.value.step === 1) {
      if (!draft.value.profile.name.trim()) throw new Error('请填写姓名');
      if (!draft.value.profile.email.trim() && !draft.value.profile.phone.trim())
        throw new Error('请至少填写一种联系方式');
      if (!draft.value.direction.trim()) throw new Error('请填写求职方向');
    }
    if (draft.value.step === 2) {
      if (draft.value.experiences.some((e) => !e.excluded && !e.confirmed))
        throw new Error('请确认采用的经历，或勾选暂不采用');
      await saveExperiences();
      await submitJdDraft();
    }
    if (draft.value.step === 3 && draft.value.backend?.activeFollowupSessionId) {
      const session = await api<Schema<'FollowupView'>>(
        `/api/followup-sessions/${draft.value.backend.activeFollowupSessionId}`,
      );
      if (session.status !== 'COMPLETED')
        throw new Error('请先完成或提前结束智能追问，再进入模板选择');
    }
    const nextStep = Math.min(4, draft.value.step + 1);
    await saveWorkspace((['JD', 'PROFILE', 'MATERIALS', 'FOLLOWUP', 'EDITOR'] as const)[nextStep]);
    draft.value.step = nextStep;
  });
}
function addExperience() {
  draft.value.experiences.push({
    id: crypto.randomUUID(),
    type: '项目经历',
    title: '',
    role: '',
    period: '',
    description: '',
    confirmed: false,
    excluded: false,
  });
}
async function extract() {
  await run(async () => {
    if (!draft.value.materialsText.trim()) throw new Error('请先填写文字材料');
    await saveExperiences();
    const accepted = await api<Schema<'AsyncAccepted'>>('/api/materials', 'POST', {
      workspaceId: draft.value.backend!.id,
      kind: 'TEXT',
      text: draft.value.materialsText,
    });
    await waitTask(accepted.taskId);
    draft.value.materialsText = '';
    await refreshWorkspace(draft.value.backend!.id);
    success('AI 已提取经历，请逐项核对并确认');
  });
}
async function upload(files: File[]) {
  await run(async () => {
    await saveExperiences();
    for (const file of files) {
      if (file.size > 20 * 1024 * 1024) throw new Error(file.name + ' 超过 20MB');
      const uploaded = await uploadFile(file, 'MATERIAL');
      const accepted = await api<Schema<'AsyncAccepted'>>('/api/materials', 'POST', {
        workspaceId: draft.value.backend!.id,
        kind: 'FILE',
        fileId: uploaded.id,
        title: file.name,
      });
      await waitTask(accepted.taskId);
    }
    await refreshWorkspace(draft.value.backend!.id);
    success('文件已上传并完成提取，请核对经历卡片');
  });
}
async function merge() {
  await run(async () => {
    const chosen = draft.value.experiences.filter((e) => selected.value.includes(e.id));
    if (chosen.length < 2 || new Set(chosen.map((e) => e.type)).size !== 1)
      throw new Error('请至少选择两张同类型卡片');
    await saveExperiences();
    const target = chosen[0]!;
    const merged = experienceData({
      ...target,
      description: chosen.map((e) => e.description).join('\n'),
    });
    await api('/api/experience-merges', 'POST', {
      targetExperienceId: target.id,
      sources: chosen.map((e) => ({ id: e.id, revision: e.backend!.revision })),
      data: merged,
      status: 'CANDIDATE',
      excluded: false,
      sourceMappings: mergeSources(
        merged,
        chosen.map((e) => e.backend!),
      ),
    });
    selected.value = [];
    await refreshWorkspace(draft.value.backend!.id);
    success('已合并经历，请重新核对');
  });
}
async function removeExperience(index: number) {
  await run(async () => {
    const e = draft.value.experiences[index]!;
    if (e.backend) await api(`/api/experiences/${e.id}`, 'DELETE');
    draft.value.experiences.splice(index, 1);
  });
}
const pendingMaterial = ref<{ index: number; messages: string[] } | null>(null);
async function removeMaterial(index: number) {
  await run(async () => {
    const m = draft.value.files[index]!;
    if (!m.materialId) {
      draft.value.files.splice(index, 1);
      return;
    }
    const impact = await api<Schema<'Impact'>>(`/api/materials/${m.materialId}/deletion-impact`);
    pendingMaterial.value = { index, messages: impact.messages };
  });
}
async function confirmRemoveMaterial() {
  await run(async () => {
    const index = pendingMaterial.value!.index,
      m = draft.value.files[index]!;
    await api(`/api/materials/${m.materialId}`, 'DELETE');
    draft.value.files.splice(index, 1);
    pendingMaterial.value = null;
  });
}
const generationCompleted = ref(false);
onBeforeRouteLeave(
  () => (!busy.value && !jdBusy.value && !followupBusy.value) || generationCompleted.value,
);
async function chooseTemplateAndGenerate(template: ResumeTemplateId) {
  if (busy.value) return;
  draft.value.template = template;
  await generate();
}
async function generate() {
  await run(async () => {
    await saveExperiences();
    const w = await saveWorkspace('EDITOR');
    const accepted = await api<Schema<'AsyncAccepted'>>('/api/resume-generations', 'POST', {
      workspaceId: w.id,
      baseWorkspaceRevision: w.revision,
      experienceRevisions: draft.value.experiences
        .filter((e) => e.confirmed && !e.excluded)
        .map((e) => ({ id: e.id, revision: e.backend!.revision })),
      templateId: draft.value.template,
      templateVersion: '1.1.0',
      sectionTypes: [
        'EDUCATION',
        ...new Set(
          draft.value.experiences
            .filter((e) => e.confirmed && !e.excluded && e.backend)
            .map(
              (e) =>
                (
                  ({
                    PROJECT: 'PROJECTS',
                    INTERNSHIP: 'INTERNSHIPS',
                    CAMPUS: 'CAMPUS',
                    AWARD: 'AWARDS',
                  }) as const
                )[e.backend!.type],
            ),
        ),
        'SKILLS',
      ],
      title: draft.value.title || draft.value.direction + ' · 我的简历',
    });
    generationTaskId.value = accepted.taskId;
    const result = await resource<Schema<'ResumeOutput'>>(accepted);
    const doc = await refreshResume(result.id);
    generationCompleted.value = true;
    success('AI 简历已生成，请核对内容');
    await router.push('/resumes/' + doc.id + '/edit');
  });
}
</script>
<template>
  <div
    class="page-container creation-session-page"
    :class="{ 'template-gallery-page': draft.step === 4 }"
  >
    <PageHeading
      v-if="draft.step < 4"
      eyebrow="CREATE WITH CONFIDENCE"
      title="制作简历"
      description="不必一次写得完美，我们陪你一步步整理。"
      ><BaseButton variant="secondary" :disabled="busy" @click="router.push('/dashboard')"
        >退出制作</BaseButton
      ></PageHeading
    >
    <ElSteps
      v-if="draft.step < 4"
      :active="draft.step"
      finish-status="finish"
      align-center
      class="creation-steps"
      ><ElStep v-for="name in steps" :key="name" :title="name"
    /></ElSteps>
    <div class="creation-grid">
      <section class="panel wizard-panel" :class="{ 'template-stage': draft.step === 4 }">
        <template v-if="draft.step === 0"
          ><h2 class="wrap-heading">目标岗位与求职方向</h2>
          <small class="step-context">第 1 步 / 共 4 步</small>
          <p class="body-copy">岗位 JD 能让简历更有针对性，没有也可以跳过。</p>
          <label class="field"
            >简历名称 *<ElInput
              v-model="draft.title"
              maxlength="100"
              placeholder="例如：前端开发 / 校招"
              :aria-invalid="Boolean(fieldErrors.title)"
              aria-label="简历名称"
            /><small v-if="fieldErrors.title" class="field-validation-error" role="alert">{{
              fieldErrors.title
            }}</small></label
          ><label class="field"
            >求职方向 *<ElInput
              v-model="draft.direction"
              maxlength="100"
              placeholder="例如：前端开发工程师"
              :aria-invalid="Boolean(fieldErrors.direction)"
              aria-label="求职方向"
            /><small v-if="fieldErrors.direction" class="field-validation-error" role="alert">{{
              fieldErrors.direction
            }}</small></label
          ><label class="field"
            >选择已存档的岗位 JD<ElSelect v-model="draft.jdId" aria-label="选择已存档的岗位 JD"
              ><ElOption value="" :label="'暂不关联，直接制作通用简历'" />
              <ElOption
                v-for="jd in state.jds"
                :key="jd.id"
                :value="jd.id"
                :label="
                  String(jd.title) + ' ' + '/' + ' ' + String(jd.company || '未填写公司')
                " /></ElSelect
          ></label>
          <div v-if="draft.jdId" class="callout">
            <strong>已选岗位要求</strong>
            <p>{{ state.jds.find((j) => j.id === draft.jdId)?.text }}</p>
          </div>
          <BaseButton
            variant="ghost"
            :disabled="busy || jdBusy"
            :aria-expanded="jdEditorOpen"
            aria-controls="inline-jd-editor"
            @click="jdEditorOpen = !jdEditorOpen"
          >
            {{ jdEditorOpen ? '收起岗位 JD' : '添加岗位 JD' }} <Plus :size="15" />
          </BaseButton>
          <Transition name="jd-expand">
            <section
              v-show="jdEditorOpen"
              id="inline-jd-editor"
              class="inline-jd-editor"
              aria-label="添加岗位 JD"
            >
              <h3>添加岗位 JD</h3>
              <JdEditor
                :key="jdEditorKey"
                draft-only
                :initial-text="jdDraft.text"
                :initial-file="jdDraft.file"
                @draft="jdDraft = $event"
                :direction="draft.direction"
                @busy="jdBusy = $event"
                @saved="jdSaved"
              />
            </section>
          </Transition>
        </template>
        <template v-if="draft.step === 1"
          ><h2 class="wrap-heading">填写基本资料</h2>
          <ProfilePhoto v-model="draft.profile.photoData" />
          <small class="step-context">第 2 步 / 共 4 步</small>
          <p class="body-copy">这些信息将显示在简历中，账户昵称与真实姓名相互独立。</p>
          <div class="form-grid">
            <label class="field"
              >姓名 *<ElInput
                v-model="draft.profile.name"
                maxlength="50"
                placeholder="你的真实姓名"
                :aria-invalid="Boolean(fieldErrors.name)"
                aria-label="姓名"
              /><small v-if="fieldErrors.name" class="field-validation-error" role="alert">{{
                fieldErrors.name
              }}</small></label
            ><label class="field"
              >求职方向 *<ElInput
                v-model="draft.direction"
                maxlength="100"
                :aria-invalid="Boolean(fieldErrors.direction)"
                aria-label="求职方向"
              /><small v-if="fieldErrors.direction" class="field-validation-error" role="alert">{{
                fieldErrors.direction
              }}</small></label
            ><label class="field"
              >邮箱<ElInput
                v-model="draft.profile.email"
                maxlength="100"
                placeholder="name@example.com"
                type="email"
                :aria-invalid="Boolean(fieldErrors.email)"
                aria-label="邮箱"
              /><small v-if="fieldErrors.email" class="field-validation-error" role="alert">{{
                fieldErrors.email
              }}</small></label
            ><label class="field"
              >手机号<ElInput
                v-model="draft.profile.phone"
                maxlength="30"
                type="tel"
                :aria-invalid="Boolean(fieldErrors.phone)"
                aria-label="手机号"
              /><small v-if="fieldErrors.phone" class="field-validation-error" role="alert">{{
                fieldErrors.phone
              }}</small></label
            ><label class="field"
              >学校<ElInput
                v-model="draft.profile.school"
                maxlength="100"
                aria-label="学校" /></label
            ><label class="field"
              >专业<ElInput
                v-model="draft.profile.major"
                maxlength="100"
                aria-label="专业" /></label
            ><label class="field"
              >学历<ElSelect v-model="draft.profile.degree" aria-label="学历"
                ><ElOption :value="'本科'" :label="'本科'" />
                <ElOption :value="'硕士'" :label="'硕士'" />
                <ElOption :value="'博士'" :label="'博士'" />
                <ElOption :value="'大专'" :label="'大专'" />
                <ElOption :value="'其他'" :label="'其他'" /></ElSelect></label
            ><label class="field"
              >教育时间<EducationDates
                v-model="draft.profile.educationPeriod"
            /></label>
          </div>
          <AdditionalEducation :profile="draft.profile" /><label class="field"
            >技能<ElInput
              v-model="draft.profile.skills"
              :rows="3"
              maxlength="2000"
              placeholder="自由描述掌握的技术、工具和能力"
              type="textarea"
              aria-label="技能" /></label
          ><BaseButton
            variant="ghost"
            @click="
              draft.profile = exampleProfile();
              draft.direction = '前端开发';
              notify('已填入虚构示例资料，请替换为自己的信息');
            "
            >填入示例资料，快速体验</BaseButton
          ></template
        >
        <template v-if="draft.step === 2"
          ><h2 class="wrap-heading">整理并确认经历</h2>
          <small class="step-context">第 3 步 / 共 4 步</small>
          <p class="body-copy">粘贴材料或手动填写。只有确认采用的经历会进入简历。</p>
          <FileUpload
            class="upload-zone"
            accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg"
            multiple
            :disabled="busy"
            @select="upload"
            ><Upload :size="24" /><strong>点击选择文件</strong
            ><small>PDF / DOCX / TXT / Markdown / PNG / JPG / 单个 20MB 以内</small></FileUpload
          >
          <p class="field-hint">文件将上传至后端解析并生成待确认经历；解析失败会显示实际错误。</p>
          <div v-for="(file, index) in draft.files" :key="index" class="attachment-row">
            <FileText :size="16" /><span>{{ file.name }}</span
            ><MaterialDetails v-if="file.materialId" :material-id="file.materialId" /><small
              v-if="file.size"
              >{{ Math.ceil(file.size / 1024) }} KB</small
            ><button
              class="icon-button"
              :aria-label="'移除' + file.name"
              @click="removeMaterial(index)"
            >
              <Trash2 :size="15" />
            </button>
          </div>
          <label class="field"
            >文字材料<ElInput
              v-model="draft.materialsText"
              :rows="4"
              maxlength="100000"
              placeholder="写下课程项目、实习或校园活动，尽量描述真实的个人贡献…"
              type="textarea"
              aria-label="文字材料"
            />
          </label>
          <div class="inline-actions">
            <BaseButton size="small" @click="extract"
              ><Sparkles :size="15" />从原文整理卡片</BaseButton
            ><BaseButton size="small" variant="secondary" @click="addExperience"
              ><Plus :size="15" />手动添加经历</BaseButton
            ><BaseButton size="small" variant="ghost" @click="merge"
              ><Merge :size="15" />合并选中项</BaseButton
            >
          </div>
          <div
            v-for="(experience, index) in draft.experiences"
            :key="experience.id"
            class="experience-card"
          >
            <div class="experience-heading">
              <ElCheckbox
                class="check-label"
                :model-value="selected.includes(experience.id)"
                @update:model-value="(value) => selectExperience(experience.id, Boolean(value))"
                >经历 {{ index + 1 }}</ElCheckbox
              ><span v-if="experience.confirmed" class="pill green">已确认</span
              ><button
                class="icon-button danger-icon"
                :aria-label="'删除经历' + (index + 1)"
                @click="removeExperience(index)"
              >
                <Trash2 :size="16" />
              </button>
            </div>
            <div class="form-grid" @input="experience.confirmed = false">
              <label class="field"
                >类型<ElSelect
                  :disabled="busy"
                  v-model="experience.type"
                  @change="experience.confirmed = false"
                  aria-label="类型"
                  ><ElOption :value="'项目经历'" :label="'项目经历'" />
                  <ElOption :value="'实习经历'" :label="'实习经历'" />
                  <ElOption :value="'校园经历'" :label="'校园经历'" />
                  <ElOption :value="'获奖经历'" :label="'获奖经历'" /></ElSelect></label
              ><label class="field"
                >名称<ElInput v-model="experience.title" maxlength="100" aria-label="名称" /></label
              ><label class="field"
                >职责 / 角色<ElInput
                  v-model="experience.role"
                  maxlength="100"
                  aria-label="职责 / 角色" /></label
              ><label class="field"
                >时间<ElInput v-model="experience.period" maxlength="60" aria-label="时间"
              /></label>
            </div>
            <label class="field"
              >实际贡献与结果<ElInput
                v-model="experience.description"
                :rows="4"
                maxlength="10000"
                @input="experience.confirmed = false"
                type="textarea"
                aria-label="实际贡献与结果"
              />
            </label>
            <div class="inline-actions">
              <ElCheckbox
                class="check-label"
                v-model="experience.confirmed"
                :disabled="!experience.title.trim() || !experience.description.trim()"
                >已核对，确认采用</ElCheckbox
              ><ElCheckbox class="check-label" v-model="experience.excluded">暂不采用</ElCheckbox>
            </div>
          </div>
          <p v-if="!draft.experiences.length" class="field-hint">
            暂时没有经历也没关系，可以继续通过补充追问梳理。
          </p></template
        >
        <template v-if="draft.step === 3"
          ><h2>补充经历信息</h2>
          <FollowupPanel @busy="followupBusy = $event" @completed="followupCompleted"
        /></template>
        <template v-if="draft.step === 4">
          <TemplateGallery
            :model-value="draft.template"
            :disabled="busy"
            @update:model-value="chooseTemplateAndGenerate"
          />
          <p v-if="!busy" class="field-hint">点击喜欢的模板，生成完成后将自动进入简历编辑。</p>
        </template>
        <div v-if="draft.step === 4 && busy" class="callout" role="status">
          <strong>{{ generationStatus }}</strong>
          <p v-if="busy">完成后会自动打开可编辑的简历页面，请勿重复提交。</p>
        </div>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <footer v-if="draft.step < 4" class="wizard-footer">
          <BaseButton
            variant="secondary"
            :disabled="draft.step === 0 || busy || followupBusy"
            @click="
              draft.step--;
              error = '';
            "
            ><ArrowLeft :size="15" />上一步</BaseButton
          ><span>{{ draft.step < 4 ? `${draft.step + 1} / 4` : '简历模板' }}</span
          ><BaseButton
            v-if="draft.step < 4"
            :disabled="jdBusy || followupBusy"
            :loading="busy"
            @click="next"
            >{{ draft.step === 0 && !draft.jdId && !hasJdDraft ? '跳过 JD，继续' : '下一步'
            }}<ArrowRight :size="15" /></BaseButton
          ><BaseButton v-else :disabled="busy" :loading="busy" @click="generate"
            ><Sparkles :size="16" />{{
              busy ? '正在生成，完成后自动进入编辑页…' : 'AI 生成并进入编辑器'
            }}</BaseButton
          >
        </footer>
      </section>
    </div>
    <BaseModal :open="!!pendingMaterial" title="删除材料？" @close="pendingMaterial = null"
      ><p v-for="message in pendingMaterial?.messages" :key="message">{{ message }}</p>
      <BaseButton :loading="busy" @click="confirmRemoveMaterial">确认删除</BaseButton></BaseModal
    >
  </div>
</template>

<style scoped>
.creation-session-page {
  width: 100%;
  max-width: 960px;
  margin-inline: auto;
  padding: 40px 24px 64px;
}
.creation-session-page .creation-grid {
  display: block;
}
.creation-session-page .wizard-panel {
  width: 100%;
  min-width: 0;
}
@media (max-width: 640px) {
  .creation-session-page {
    padding: 24px 16px 40px;
  }
  .creation-session-page .wizard-panel {
    padding: 24px 18px;
  }
}
</style>

<style scoped>
.inline-jd-editor {
  margin-top: 20px;
  padding-top: 24px;
  border-top: 1px solid #dedbed;
}
.jd-expand-enter-active,
.jd-expand-leave-active {
  transition:
    opacity 0.2s,
    transform 0.2s;
}
.jd-expand-enter-from,
.jd-expand-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
@media (prefers-reduced-motion: reduce) {
  .jd-expand-enter-active,
  .jd-expand-leave-active {
    transition: none;
  }
}
</style>

<style scoped>
.template-stage {
  border-top: 4px solid #969be7;
  background: linear-gradient(145deg, #fcf8fb, #fff 60%);
  margin-top: 24px;
}
</style>

<style scoped>
.creation-session-page.template-gallery-page {
  max-width: 1440px;
  padding-top: 40px;
}
.template-gallery-page .wizard-panel.template-stage {
  border: 0;
  background: transparent;
  box-shadow: none;
  margin: 0;
  padding: 0;
}
.template-gallery-page .callout {
  max-width: 664px;
  margin: 32px auto 16px;
  background: #fff;
  border: 1px solid #e8e5ee;
  border-radius: 12px;
}
.template-gallery-page .field-hint {
  text-align: center;
}
.template-gallery-page .wizard-footer {
  max-width: 1000px;
  margin: 32px auto 0;
}
</style>

<style scoped>
.field-validation-error {
  display: block;
  color: #bf3653;
  font-size: 13px;
  margin-top: 6px;
}
.field:has([aria-invalid='true']) :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #bf3653 inset;
}
</style>
