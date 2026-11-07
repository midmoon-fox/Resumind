import type { Schema } from './schema';

type Session = Schema<'FollowupView'>;

/** Skip remaining questions without altering previously confirmed experience. */
export async function finishFollowup(
  session: Session,
  complete: (body: { baseRevision: number; reason: string }) => Promise<unknown>,
): Promise<void> {
  if (session.status === 'COMPLETED') return;
  await complete({ baseRevision: session.revision, reason: '用户点击下一步，跳过剩余追问' });
}

type FollowupPorts = {
  read: () => Promise<Session>;
  wait: (taskId: string) => Promise<unknown>;
  post: (suffix: string, body: Record<string, unknown>) => Promise<unknown>;
  active: () => boolean;
};

/** Run intermediate states in order; only an answerable question or completion reaches the UI. */
export async function advanceFollowup(
  initial: Session,
  ports: FollowupPorts,
): Promise<Session | null> {
  let current = initial;
  for (let transitions = 0; transitions < 16; transitions++) {
    if (!ports.active()) return null;
    if (current.pendingTaskId) {
      await ports.wait(current.pendingTaskId);
      if (!ports.active()) return null;
      current = await ports.read();
      continue;
    }
    if (current.status === 'COMPLETED' || current.status === 'AWAITING_ANSWER') return current;
    if (current.status === 'FAILED')
      throw new Error(current.error?.message || '问题准备失败，请在后台任务中重试后重新加载');
    if (current.status === 'REVIEW_REQUIRED') {
      const turn = current.turns.find((t) => t.id === current.currentTurnId);
      if (!turn) throw new Error('未找到当前问题，请重新加载追问状态');
      await ports.post('answer-confirmations', {
        baseRevision: current.revision,
        turnId: turn.id,
        updates: turn.candidateUpdates.map((candidate) => ({
          candidateId: candidate.candidateId,
          experienceId: candidate.experienceId,
          baseExperienceRevision: candidate.baseExperienceRevision,
          data: {
            ...candidate.proposedData,
            startDate: candidate.proposedData.startDate || null,
            endDate: candidate.proposedData.isCurrent
              ? null
              : candidate.proposedData.endDate || null,
          },
        })),
      });
    } else if (current.status === 'READY_NEXT') {
      await ports.post('next-questions', { baseRevision: current.revision });
    } else {
      throw new Error('追问状态正在更新，请稍后重新加载；已提交的回答会保留');
    }
    if (!ports.active()) return null;
    current = await ports.read();
  }
  throw new Error('追问状态暂未同步，请重新加载；已提交的回答会保留');
}
