import { ref } from 'vue';
import { suggestionText } from '../services/aiSuggestionText';
import { validateAiTarget } from '../services/aiTargetValidation';
import { ElMessageBox } from 'element-plus';
import type { ResumeDocument } from '../types/app';
import { api } from '../services/client';
import { resource } from '../services/tasks';
import type { Schema } from '../services/schema';

interface AiFieldOptions {
  getDoc: () => ResumeDocument | undefined;
  saveResume: (doc: ResumeDocument) => Promise<unknown>;
  refreshResume: (id: string) => Promise<unknown>;
  onApplied?: () => void;
}

type SuggestionValue =
  Schema<'SuggestionView_Union_RichNode__SuggestionSectionContent__SuggestionEducationContent__SuggestionSkillsContent__'>;

export function useAiFieldWriter(options: AiFieldOptions) {
  const busy = ref(false);
  const notice = ref('');
  const activeKey = ref('');
  const pending = ref<{
    id: string;
    key: string;
    text: string;
    resumeId: string;
    revision: number;
    original: string;
    needsFactConfirmation: boolean;
    confirmationHint?: string;
  } | null>(null);

  function fail(message: string) {
    notice.value = `啊噢，出错了。${message}`;
  }

  async function apply() {
    const suggestion = pending.value;
    if (!suggestion || busy.value) return;
    if (suggestion.needsFactConfirmation) {
      notice.value = '生成内容含未核实事实，暂不能应用，请补充真实资料后重新生成';
      return;
    }
    try {
      await ElMessageBox.confirm(
        '确认是否应用？应用后将覆盖上方原有内容，可通过撤销恢复。',
        '确认是否应用',
        { confirmButtonText: '确认应用', cancelButtonText: '取消', type: 'warning' },
      );
    } catch {
      return;
    }
    busy.value = true;
    try {
      const doc = options.getDoc();
      if (
        !doc ||
        doc.id !== suggestion.resumeId ||
        doc.revision !== suggestion.revision ||
        JSON.stringify([doc.profile, doc.sections, doc.role]) !== suggestion.original
      ) {
        return fail('原文已发生变化，请重新生成后再应用。');
      }
      await api(`/api/suggestions/${suggestion.id}/applications`, 'POST', {
        baseRevision: doc.revision,
      });
      await options.refreshResume(doc.id);
      pending.value = null;
      notice.value = '已应用到上方文本框，可撤销';
      options.onApplied?.();
    } catch {
      fail('暂时无法应用这条建议，请稍后重试。');
    } finally {
      busy.value = false;
    }
  }

  async function run(
    target: { kind: string; sectionId?: string; itemId?: string; field?: string },
    instruction: string,
  ) {
    if (busy.value) return;
    busy.value = true;
    activeKey.value =
      target.field === 'skills' ? 'skills' : `${target.sectionId}:${target.itemId || target.field}`;
    pending.value = null;
    notice.value = '正在生成…';
    try {
      const doc = options.getDoc();
      if (!doc) return fail('请重新打开简历后再试。');
      const problem = validateAiTarget(doc, target);
      if (problem) return fail(problem + '。');
      await options.saveResume(doc);
      const persisted = doc.backend?.document.sections.find(
        (section) => section.id === target.sectionId,
      );
      if (!persisted) return fail('请先保存这个模块，再使用 AI 帮助。');
      const original = JSON.stringify([doc.profile, doc.sections, doc.role]);
      const revision = doc.revision;
      const accepted = await api<Schema<'AsyncAccepted'>>(
        `/api/resumes/${doc.id}/suggestions`,
        'POST',
        { baseRevision: doc.revision, target, instruction },
      );
      const result = await resource<SuggestionValue>(accepted);
      if (result.status !== 'READY') {
        return fail('建议还没准备好，请稍后查看。');
      }
      const generatedText = suggestionText(result.proposed)
        .replace(/\u200b/g, '')
        .trim();
      if (!generatedText) {
        return fail('没有生成可用的内容，可以补充一些具体信息后再试。');
      }
      if (
        options.getDoc()?.id !== doc.id ||
        doc.revision !== revision ||
        JSON.stringify([doc.profile, doc.sections, doc.role]) !== original
      ) {
        return fail('你已修改或切换简历，请重新生成。');
      }
      pending.value = {
        id: result.id,
        key: activeKey.value,
        text: generatedText,
        resumeId: doc.id,
        revision,
        original,
        needsFactConfirmation: result.needsFactConfirmation,
        confirmationHint: result.needsFactConfirmation ? result.explanation.trim() : undefined,
      };
      notice.value = result.needsFactConfirmation
        ? '生成结果包含待核实信息，暂不能应用'
        : '生成完成，请查看下方内容后点击应用';
    } catch {
      fail('暂时没能生成可用内容，请稍后重试。');
    } finally {
      busy.value = false;
    }
  }

  return { busy, notice, run, pending, apply, activeKey };
}
