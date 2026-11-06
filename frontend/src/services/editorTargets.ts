// 预览联动编辑：iframe 桥接消息协议与目标校验

export interface EditTarget {
  // 左侧折叠卡片键：'basic' | 'education' | 'skills' | section.id
  key: string;
  // 普通条目 id（列表模块），其余为 null
  itemId: string | null;
  // 字段名：name | intention | description | education | skills 等
  field: string | null;
}

interface PreviewSelectMessage {
  type: 'resume-preview:select';
  bridgeVersion: number;
  channel: string;
  resumeId: string;
  revision: number;
  target: EditTarget;
}

export function parsePreviewMessage(
  data: unknown,
  expected: { channel: string; resumeId: string; revision: number },
): EditTarget | null {
  if (!data || typeof data !== 'object') return null;
  const m = data as Partial<PreviewSelectMessage>;
  if (m.type !== 'resume-preview:select') return null;
  if (m.bridgeVersion !== 1) return null;
  if (m.channel !== expected.channel) return null;
  if (m.resumeId !== expected.resumeId) return null;
  if (typeof m.revision !== 'number' || m.revision !== expected.revision) return null;
  const t = m.target;
  if (!t || typeof t !== 'object') return null;
  if (typeof t.key !== 'string' || !t.key) return null;
  return {
    key: t.key,
    itemId: typeof t.itemId === 'string' && t.itemId ? t.itemId : null,
    field: typeof t.field === 'string' && t.field ? t.field : null,
  };
}
