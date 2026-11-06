import { reactive } from 'vue';
import { api } from './client';
import type { Schema } from './schema';
export const tasks = reactive<Schema<'TaskView'>[]>([]);
let epoch = 0;
export function clearTasks() {
  epoch++;
  tasks.splice(0);
}
function put(task: Schema<'TaskView'>) {
  const index = tasks.findIndex((t) => t.id === task.id);
  if (index < 0) tasks.unshift(task);
  else tasks[index] = task;
}
export async function waitTask(id: string) {
  const startedEpoch = epoch;
  for (let i = 0; i < 300; i++) {
    if (epoch !== startedEpoch) throw new Error('会话已切换，已停止查询');
    const task = await api<Schema<'TaskView'>>(`/api/tasks/${id}`).catch((e) => {
      throw new Error(
        `查询任务 ${id} 失败：${e instanceof Error ? e.message : '网络错误'}；可在任务面板继续查询，勿重复提交。`,
      );
    });
    if (epoch !== startedEpoch) throw new Error('会话已切换，已停止查询');
    put(task);
    if (task.status === 'SUCCEEDED') return task;
    if (task.status === 'FAILED' || task.status === 'CANCELLED')
      throw new Error(
        `${task.error?.message ?? (task.status === 'CANCELLED' ? '任务已取消' : '任务失败')}（任务 ${id}）`,
      );
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error('任务仍在后台处理中，请在任务面板查询结果，不要重复提交');
}
export async function resource<T>(accepted: Schema<'AsyncAccepted'>): Promise<T> {
  await waitTask(accepted.taskId);
  return api<T>(accepted.resourceUrl);
}
export async function retryTask(task: Schema<'TaskView'>) {
  await api(`/api/tasks/${task.id}/retries`, 'POST', { expectedAttempt: task.attempt });
  return waitTask(task.id);
}
export async function cancelTask(task: Schema<'TaskView'>) {
  await api(`/api/tasks/${task.id}/cancellations`, 'POST');
  put(await api<Schema<'TaskView'>>(`/api/tasks/${task.id}`));
}
