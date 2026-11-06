import type { Schema } from './schema';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
  ) {
    super(message);
  }
}
export const AUTH_STORAGE_KEY = 'resume-star-jwt-v1';
let accessToken = '';
let expiresAt = 0;
const pendingIntents = new Map<string, string>();
export function setAccessToken(value: string, expiry?: string): boolean {
  accessToken = value;
  expiresAt = expiry ? Date.parse(expiry) : 0;
  if (expiry) {
    if (!Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
      clearSessionToken();
      throw new ApiError(401, 'TOKEN_EXPIRED', '登录凭证已到期，请重新登录');
    }
    try {
      localStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({ accessToken: value, expiresAt: expiry }),
      );
    } catch {
      return false;
    }
  }
  return true;
}
export function restoreAccessToken(): boolean {
  if (accessToken && (!expiresAt || expiresAt > Date.now())) return true;
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return false;
    const saved = JSON.parse(raw);
    if (
      typeof saved.accessToken !== 'string' ||
      !saved.accessToken ||
      saved.accessToken.length > 4096 ||
      !Number.isFinite(Date.parse(saved.expiresAt)) ||
      Date.parse(saved.expiresAt) <= Date.now()
    ) {
      clearSessionToken();
      return false;
    }
    accessToken = saved.accessToken;
    expiresAt = Date.parse(saved.expiresAt);
    return true;
  } catch {
    clearSessionToken();
    return false;
  }
}
export function clearSessionToken() {
  accessToken = '';
  expiresAt = 0;
  pendingIntents.clear();
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    /* Storage can be unavailable. */
  }
}
export async function authenticatedFetch(path: string, options: RequestInit = {}) {
  if (accessToken && expiresAt && expiresAt <= Date.now()) {
    clearSessionToken();
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('session-expired'));
    throw new ApiError(401, 'TOKEN_EXPIRED', '登录已到期，请重新登录');
  }
  const headers = new Headers(options.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const authenticated = !!accessToken;
  const response = await fetch(path, { ...options, headers, credentials: 'omit' });
  if (response.status === 401 && authenticated && !path.startsWith('/api/auth/')) {
    clearSessionToken();
    if (typeof window !== 'undefined') window.dispatchEvent(new Event('session-expired'));
  }
  return response;
}
if (typeof window !== 'undefined')
  window.addEventListener('storage', (event) => {
    if (event.key === AUTH_STORAGE_KEY) window.location.reload();
  });
export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  if (!path.startsWith('/api/')) throw new Error('接口必须使用同源 /api/ 路径');
  const write = method !== 'GET';
  const form = body instanceof FormData;
  const serialized =
    body === undefined ? undefined : form ? (body as FormData) : JSON.stringify(body);
  // Retain the same intent key after an unknown transport outcome. Never blindly duplicate writes.
  const fingerprint =
    method +
    path +
    (form
      ? JSON.stringify(
          Array.from(body.entries()).map(([k, v]) => [
            k,
            typeof v === 'string' ? v : [v.name, v.size, v.lastModified],
          ]),
        )
      : (serialized ?? ''));
  const needsKey = write && path !== '/api/auth/session' && !path.endsWith('/preflights');
  const intentKey = pendingIntents.get(fingerprint) ?? crypto.randomUUID();
  if (needsKey) pendingIntents.set(fingerprint, intentKey);
  const headers: Record<string, string> = {};
  if (needsKey) headers['Idempotency-Key'] = intentKey;
  if (body !== undefined && !form) headers['Content-Type'] = 'application/json';
  let response: Response;
  try {
    response = await authenticatedFetch(path, {
      method,
      headers,
      body: serialized,
      signal: AbortSignal.timeout(45000),
    });
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(
      0,
      'NETWORK_UNKNOWN',
      write
        ? '连接中断，操作结果尚未确认。请恢复连接后重试同一操作，系统会沿用原请求编号。'
        : '连接失败，请检查网络和后端服务后重试',
    );
  }
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (response.ok) {
    if (response.status !== 204 && (!payload || !Object.hasOwn(payload, 'data')))
      throw new ApiError(502, 'INVALID_RESPONSE', '服务端响应格式不符合接口约定');
    pendingIntents.delete(fingerprint);
    return payload?.data as T;
  }
  const error = payload?.error;
  if (response.status < 500) pendingIntents.delete(fingerprint);
  const details = Array.isArray(error?.details) ? error.details : error?.details?.errors;
  const detail = Array.isArray(details)
    ? details
        .map((d: { path?: string; message?: string }) => `${d.path ?? ''} ${d.message ?? ''}`)
        .join('；')
    : '';
  throw new ApiError(
    response.status,
    error?.code ?? 'HTTP_ERROR',
    (error?.message ?? `请求失败（${response.status}）`) +
      (detail ? '：' + detail : '') +
      (payload?.requestId ? `（请求 ${payload.requestId}）` : ''),
    payload?.requestId,
  );
}
export async function allPages<T>(path: string): Promise<T[]> {
  const items: T[] = [];
  for (let page = 1; ; page++) {
    const result = await api<{ items: T[]; total: number }>(
      `${path}${path.includes('?') ? '&' : '?'}page=${page}&pageSize=20`,
    );
    items.push(...result.items);
    if (items.length >= result.total || !result.items.length) return items;
  }
}
export function localFileUrl(url: string) {
  const parsed = new URL(url, window.location.origin);
  if (!/^\/internal\/files\/[0-9a-f-]{36}$/.test(parsed.pathname))
    throw new Error('无效的文件下载地址');
  return parsed.pathname + parsed.search;
}
export async function download(path: string, filename: string) {
  const data = await api<Schema<'Download'>>(path);
  const response = await authenticatedFetch(localFileUrl(data.url));
  if (!response.ok) throw new Error('下载失败，链接可能已过期，请重新导出');
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
export async function uploadFile(file: File, purpose: 'MATERIAL' | 'JD' | 'AVATAR') {
  const form = new FormData();
  form.append('purpose', purpose);
  form.append('file', file);
  return api<Schema<'FileOut'>>('/api/files', 'POST', form);
}
