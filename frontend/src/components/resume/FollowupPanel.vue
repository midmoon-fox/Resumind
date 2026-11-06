<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
import BaseButton from '../common/BaseButton.vue';
import { useAppStore } from '../../composables/useAppStore';
import { api } from '../../services/client';
import { waitTask } from '../../services/tasks';
import { advanceFollowup } from '../../services/followup';
import type { Schema } from '../../services/schema';
const emit = defineEmits<{ busy: [value: boolean]; completed: [] }>();
const { state, saveExperiences, refreshWorkspace } = useAppStore();
const session = ref<Schema<'FollowupView'> | null>(null),
  busy = ref(false),
  error = ref(''),
  answer = ref('');
let active = true,
  completed = false;
const turn = computed(() =>
  session.value?.turns.find((t) => t.id === session.value?.currentTurnId),
);
watch(busy, (value) => emit('busy', value), { flush: 'sync' });
onBeforeUnmount(() => {
  active = false;
});
async function run(action: () => Promise<void>) {
  if (busy.value || !active) return;
  busy.value = true;
  error.value = '';
  try {
    await action();
  } catch (e) {
    if (active) error.value = e instanceof Error ? e.message : '追问操作失败，请重试';
  } finally {
    busy.value = false;
  }
  if (active && !error.value && session.value?.status === 'COMPLETED' && !completed) {
    completed = true;
    emit('completed');
  }
}
async function load(id: string) {
  const current = await api<Schema<'FollowupView'>>(`/api/followup-sessions/${id}`);
  if (!active) return;
  // Keep intermediate recognition details out of the question UI.
  session.value = current;
  const settled = await advanceFollowup(current, {
    active: () => active,
    wait: waitTask,
    read: () => api<Schema<'FollowupView'>>(`/api/followup-sessions/${id}`),
    post: (suffix, body) => api(`/api/followup-sessions/${id}/${suffix}`, 'POST', body),
  });
  if (!active || !settled) return;
  session.value = settled;
  if (state.workspace.backend) await refreshWorkspace(state.workspace.backend.id);
}
async function initialize() {
  await run(async () => {
    const id = session.value?.id || state.workspace.backend?.activeFollowupSessionId;
    if (id) {
      await load(id);
      return;
    }
    await saveExperiences();
    if (!active) return;
    const w = state.workspace.backend!;
    const accepted = await api<Schema<'AsyncAccepted'>>('/api/followup-sessions', 'POST', {
      workspaceId: w.id,
      baseWorkspaceRevision: w.revision,
      experienceIds: state.workspace.experiences.filter((e) => !e.excluded).map((e) => e.id),
      maxRounds: 4,
    });
    // Bind the accepted session before waiting, so refresh/recovery reuses the same session.
    session.value = await api<Schema<'FollowupView'>>(accepted.resourceUrl);
    if (active) await load(session.value.id);
  });
}
async function action(suffix: string, body: Record<string, unknown>) {
  await run(async () => {
    const current = session.value;
    if (!current) return;
    await api(`/api/followup-sessions/${current.id}/${suffix}`, 'POST', {
      baseRevision: current.revision,
      ...body,
    });
    await load(current.id);
    answer.value = '';
  });
}
async function submit() {
  if (!answer.value.trim() || !turn.value) return;
  await action('answers', { turnId: turn.value.id, answer: answer.value });
}
onMounted(() => {
  void initialize();
});
</script>
<template>
  <section :aria-busy="busy" class="followup-panel">
    <p class="body-copy">根据你的经历与岗位要求补充提问，回答后会自动保存并进入下一题。</p>
    <p v-if="busy" class="soft-note" role="status">
      {{ session ? '正在准备下一问，请稍候…' : '正在准备补充问题，请稍候…' }}
    </p>
    <template v-else-if="session?.status === 'AWAITING_ANSWER' && turn && !error">
      <p class="field-hint">第 {{ session.roundsShown }} 题 · 最多 {{ session.maxRounds }} 题</p>
      <div class="question-card">
        <h3>{{ turn.question }}</h3>
        <p>{{ turn.reason }}</p>
      </div>
      <label class="field"
        >你的真实回答
        <ElInput
          v-model="answer"
          :rows="5"
          maxlength="10000"
          type="textarea"
          aria-label="你的真实回答"
          placeholder="请描述你实际做过的事情和负责的部分。"
        />
      </label>
      <div class="inline-actions">
        <BaseButton :disabled="!answer.trim()" @click="submit">提交回答</BaseButton>
        <BaseButton variant="secondary" @click="action('skips', { turnId: turn.id })"
          >跳过这一问</BaseButton
        >
        <BaseButton variant="ghost" @click="action('completions', { reason: '用户主动结束' })"
          >结束追问，选择模板</BaseButton
        >
      </div>
    </template>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <BaseButton v-if="error" variant="secondary" :loading="busy" @click="initialize"
      >重新加载追问</BaseButton
    >
  </section>
</template>
