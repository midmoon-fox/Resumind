<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowRight, Bookmark, MapPin, BriefcaseBusiness } from '@lucide/vue';
import PageHeading from '../components/common/PageHeading.vue';
import BaseButton from '../components/common/BaseButton.vue';
import BaseModal from '../components/common/BaseModal.vue';
import { useAppStore } from '../composables/useAppStore';
import { api } from '../services/client';
import { resource } from '../services/tasks';
import type { Schema } from '../services/schema';
const { state, user, snapshot, refreshData } = useAppStore(),
  router = useRouter();
const resumeId = ref(state.resumes[0]?.id ?? ''),
  versionId = ref('');
const city = ref('Berlin'),
  direction = ref(''),
  level = ref('junior');
const busy = ref(false),
  error = ref(''),
  onlySaved = ref(false),
  query = ref('');
const run = ref<Schema<'RunView'> | null>(null),
  selected = ref<Schema<'JobView'> | null>(null);
const versions = computed(() => state.versions.filter((v) => v.resumeId === resumeId.value));
const jobs = computed(() =>
  (run.value?.jobs ?? []).filter(
    (j) =>
      (!onlySaved.value || state.favorites.includes(j.id)) &&
      (j.title + j.company + j.city).toLowerCase().includes(query.value.toLowerCase()),
  ),
);
const route = useRoute();
const runKey = () => `resume-star-last-run:${user.value?.id}`;
async function recommend() {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    const resume = state.resumes.find((r) => r.id === resumeId.value);
    if (
      !resume ||
      !city.value.trim() ||
      !(direction.value || resume.role).trim() ||
      !level.value.trim()
    )
      throw new Error('请选择简历并填写城市、求职方向和经验级别');
    const version = versionId.value
      ? state.versions.find((v) => v.id === versionId.value && v.resumeId === resumeId.value)
      : await snapshot(resume, '岗位推荐使用版本');
    if (!version) throw new Error('所选版本不属于当前简历，请重新选择');
    const accepted = await api<Schema<'AsyncAccepted'>>('/api/recommendation-runs', 'POST', {
      resumeVersionId: version.id,
      city: city.value.trim(),
      direction: (direction.value || resume.role).trim(),
      experienceLevel: level.value,
    });
    sessionStorage.setItem(runKey(), accepted.resourceId);
    run.value = await resource<Schema<'RunView'>>(accepted);
  } catch (e) {
    error.value = e instanceof Error ? e.message : '岗位推荐失败';
  } finally {
    busy.value = false;
  }
}
function favorite(id: string) {
  state.favorites = state.favorites.includes(id)
    ? state.favorites.filter((x) => x !== id)
    : [...state.favorites, id];
  persist();
}
function persist() {
  try {
    useAppStore().persist();
  } catch {
    error.value = '本机设置保存失败';
  }
}
async function archive(job: Schema<'JobView'>, use = false) {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try {
    const accepted = await api<Schema<'AsyncAccepted'>>(
      `/api/recommended-jobs/${job.id}/job-descriptions`,
      'POST',
      { title: job.company + ' · ' + job.title },
    );
    const version = await resource<Schema<'JdVersionOut'>>(accepted);
    await refreshData();
    selected.value = null;
    await router.push({ path: '/jd-library', query: use ? { jdId: version.jdId } : {} });
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存 JD 失败';
  } finally {
    busy.value = false;
  }
}
onMounted(async () => {
  const id =
    typeof route.query.runId === 'string' ? route.query.runId : sessionStorage.getItem(runKey());
  if (!id) return;
  try {
    run.value = await api<Schema<'RunView'>>(`/api/recommendation-runs/${id}`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : '推荐记录加载失败';
  }
});
</script>
<template>
  <div class="page-container">
    <PageHeading
      eyebrow="FIND YOUR NEXT STEP"
      title="岗位匹配"
      description=""
    />
    <div class="panel">
      <div class="form-grid">
        <label class="field"
          >选择简历<ElSelect v-model="resumeId" @change="versionId = ''" aria-label="选择简历"
            ><ElOption value="" :label="'请选择'" />
            <ElOption
              v-for="r in state.resumes"
              :key="r.id"
              :value="r.id"
              :label="String(r.title)" /></ElSelect></label
        ><label class="field"
          >使用版本<ElSelect v-model="versionId" aria-label="使用版本"
            ><ElOption value="" :label="'当前内容（创建固定版本后推荐）'" />
            <ElOption
              v-for="v in versions"
              :key="v.id"
              :value="v.id"
              :label="String(v.label) + ' ' + '·' + ' ' + String(v.createdAt)" /></ElSelect></label
        ><label class="field"
          >海外城市<ElInput
            v-model="city"
            maxlength="100"
            placeholder="例如 Berlin，或 Remote"
            aria-label="海外城市" /></label
        ><label class="field"
          >求职方向<ElInput
            v-model="direction"
            maxlength="100"
            :placeholder="state.resumes.find((r) => r.id === resumeId)?.role || '例如 Python'"
            aria-label="求职方向" /></label
        ><label class="field"
          >经验级别<ElInput
            v-model="level"
            maxlength="100"
            placeholder="例如 junior"
            aria-label="经验级别"
        /></label>
      </div>
      <BaseButton :loading="busy" @click="recommend"
        ><BriefcaseBusiness :size="17" />获取真实岗位</BaseButton
      >
      <p class="field-hint">
        当前使用海外岗位源。收藏仅保存在本机；来源未提供薪资时显示未提供，不生成虚构薪资或匹配分数。
      </p>
    </div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div class="list-toolbar">
      <label class="field"
        >筛选本次结果<ElInput
          v-model="query"
          placeholder="岗位、公司或城市"
          aria-label="筛选本次结果" /></label
      ><ElCheckbox class="check-label" v-model="onlySaved">仅看本机收藏</ElCheckbox>
    </div>
    <div v-if="jobs.length" class="job-grid">
      <article v-for="j in jobs" :key="j.id" class="panel job-card">
        <div class="job-card-top">
          <h2>{{ j.title }}</h2>
          <button
            class="icon-button"
            :aria-label="'收藏' + j.title + '（仅本机）'"
            :aria-pressed="state.favorites.includes(j.id)"
            @click="favorite(j.id)"
          >
            <Bookmark :size="19" :fill="state.favorites.includes(j.id) ? 'currentColor' : 'none'" />
          </button>
        </div>
        <p>{{ j.company }}</p>
        <strong>{{ j.salaryText || '薪资未提供' }}</strong>
        <p><MapPin :size="14" />{{ j.city }} · {{ j.availability }}</p>
        <h3>匹配依据</h3>
        <ul>
          <li v-for="r in j.reasons" :key="r">{{ r }}</li>
        </ul>
        <h3 v-if="j.gaps.length">待补充能力</h3>
        <ul>
          <li v-for="g in j.gaps" :key="g">{{ g }}</li>
        </ul>
        <small>采集时间：{{ j.fetchedAt }}</small>
        <div class="inline-actions">
          <BaseButton size="small" variant="secondary" @click="selected = j"
            >查看详情<ArrowRight :size="15" /></BaseButton
          ><BaseButton size="small" :disabled="busy" @click="archive(j)">存为 JD 并核对</BaseButton>
        </div>
      </article>
    </div>
    <div v-else class="panel app-empty">
      <h2>{{ run ? '当前结果没有匹配岗位' : '选择简历并发起岗位推荐' }}</h2>
      <p>可以调整方向、海外城市或经验条件后查询。</p>
    </div>
    <BaseModal :open="!!selected" :title="selected?.title || '岗位详情'" @close="selected = null"
      ><template v-if="selected"
        ><p>{{ selected.company }} / {{ selected.city }}</p>
        <p>{{ selected.salaryText || '来源未提供薪资' }}</p>
        <a :href="selected.sourceUrl" target="_blank" rel="noopener noreferrer">查看岗位原始页面</a>
        <p>岗位是否仍有效请以来源页面为准。</p>
        <BaseButton :loading="busy" @click="archive(selected, true)"
          >用于新简历（先核对 JD）</BaseButton
        ></template
      >
      <p v-if="error" class="form-error">{{ error }}</p></BaseModal
    >
  </div>
</template>
