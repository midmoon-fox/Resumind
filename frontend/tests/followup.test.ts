import test from 'node:test';
import assert from 'node:assert/strict';
import { advanceFollowup, finishFollowup } from '../src/services/followup.ts';

type View = Parameters<typeof advanceFollowup>[0];
function view(status: string, extra = {}): View {
  return {
    id: 'session',
    status,
    revision: 3,
    pendingTaskId: null,
    currentTurnId: 'turn',
    turns: [],
    ...extra,
  } as View;
}
test('pending question generation finishes without another click', async () => {
  const calls: string[] = [];
  const ready = view('AWAITING_ANSWER');
  const result = await advanceFollowup(view('GENERATING', { pendingTaskId: 'task' }), {
    read: async () => ready,
    wait: async (id) => {
      calls.push(id);
    },
    post: async () => {
      throw new Error('unexpected write');
    },
    active: () => true,
  });
  assert.equal(result, ready);
  assert.deepEqual(calls, ['task']);
});
test('answer facts are saved before the next question is generated', async () => {
  const calls: Array<[string, unknown]> = [];
  const states = [view('READY_NEXT'), view('AWAITING_ANSWER', { currentTurnId: 'next-turn' })];
  const candidate = {
    candidateId: 'candidate',
    experienceId: 'experience',
    baseExperienceRevision: 2,
    proposedData: { name: '项目', startDate: '', endDate: '', isCurrent: false },
    conflicts: [],
  };
  const result = await advanceFollowup(
    view('REVIEW_REQUIRED', { turns: [{ id: 'turn', candidateUpdates: [candidate] }] }),
    {
      read: async () => states.shift()!,
      wait: async () => {},
      active: () => true,
      post: async (suffix, body) => {
        calls.push([suffix, body]);
      },
    },
  );
  assert.equal(result?.currentTurnId, 'next-turn');
  assert.deepEqual(
    calls.map(([suffix]) => suffix),
    ['answer-confirmations', 'next-questions'],
  );
  const body = calls[0]![1] as {
    updates: Array<{ data: { startDate: unknown; endDate: unknown } }>;
  };
  assert.equal(body.updates[0]!.data.startDate, null);
  assert.equal(body.updates[0]!.data.endDate, null);
});
test('no questions and the last answer both finish automatically', async () => {
  let writes = 0;
  const complete = view('COMPLETED');
  const ports = {
    read: async () => complete,
    wait: async () => {},
    active: () => true,
    post: async () => {
      writes++;
    },
  };
  assert.equal(await advanceFollowup(complete, ports), complete);
  assert.equal(writes, 0);
  assert.equal(await advanceFollowup(view('READY_NEXT'), ports), complete);
  assert.equal(writes, 1);
});
test('save failures stop progression and inactive panels do not send new requests', async () => {
  const calls: string[] = [];
  const ports = {
    read: async () => view('READY_NEXT'),
    wait: async () => {},
    active: () => true,
    post: async (suffix: string) => {
      calls.push(suffix);
      throw new Error('保存失败');
    },
  };
  await assert.rejects(
    advanceFollowup(
      view('REVIEW_REQUIRED', { turns: [{ id: 'turn', candidateUpdates: [] }] }),
      ports,
    ),
    /保存失败/,
  );
  assert.deepEqual(calls, ['answer-confirmations']);
  assert.equal(await advanceFollowup(view('READY_NEXT'), { ...ports, active: () => false }), null);
  assert.deepEqual(calls, ['answer-confirmations']);
});
test('failed tasks and missing current turns never silently finish', async () => {
  const ports = {
    read: async () => view('COMPLETED'),
    wait: async () => {},
    active: () => true,
    post: async () => {
      throw new Error('unexpected write');
    },
  };
  await assert.rejects(
    advanceFollowup(view('FAILED', { error: { message: '模型暂时不可用' } }), ports),
    /模型暂时不可用/,
  );
  await assert.rejects(advanceFollowup(view('REVIEW_REQUIRED'), ports), /当前问题/);
});

test('next ends remaining questions with the current revision', async () => {
  const calls: unknown[] = [];
  await finishFollowup(view('AWAITING_ANSWER', { revision: 7 }), async (body) => {
    calls.push(body);
  });
  assert.deepEqual(calls, [{ baseRevision: 7, reason: '用户点击下一步，跳过剩余追问' }]);
});

test('next does not complete an already completed session twice', async () => {
  await finishFollowup(view('COMPLETED'), async () => {
    throw new Error('unexpected write');
  });
});

test('completion failure propagates instead of silently advancing', async () => {
  const failure = new Error('内容已更新，请重试');
  await assert.rejects(
    finishFollowup(view('AWAITING_ANSWER'), async () => {
      throw failure;
    }),
    failure,
  );
});
