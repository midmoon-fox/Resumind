export function suggestionText(value: unknown): string {
  if (Array.isArray(value)) return value.map(suggestionText).filter(Boolean).join('\n');
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object') return '';
  const node = value as Record<string, unknown>;
  if (typeof node.text === 'string') return node.text;
  if (node.content) return suggestionText(node.content);
  return Object.entries(node)
    .filter(([key]) => !['id', 'itemId', 'type', 'experienceId', 'sourceRevision'].includes(key))
    .map(([, v]) => suggestionText(v))
    .filter(Boolean)
    .join('\n');
}
