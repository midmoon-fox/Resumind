import DOMPurify from 'dompurify';

export const escapeHtml = (text: string) =>
  text.replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!,
  );
export function safeHtml(html: string) {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'span', 'a'],
    ALLOWED_ATTR: ['style', 'href', 'start', 'rel'],
  });
}
export function textHtml(text: string) {
  return text
    .split('\n')
    .map((line) => '<p>' + escapeHtml(line) + '</p>')
    .join('');
}
export function plainText(html: string) {
  const div = document.createElement('div');
  div.innerHTML = safeHtml(html).replace(/<\/(p|li)>/g, '\n');
  return (div.textContent || '').trim();
}
export function dateText(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Shanghai',
  }).format(new Date(value));
}
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename.replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_').slice(0, 160);
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
