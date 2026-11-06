/** Stable per submission, readable and distinct even within the same second. */
export function archiveTitle(direction: string, now = new Date()): string {
  const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}-${String(now.getMilliseconds()).padStart(3, '0')}`;
  return `${direction.trim() || '求职方向'} · ${stamp}`;
}
