import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  api,
  clearSessionToken,
  setAccessToken,
  authenticatedFetch,
  allPages,
  uploadFile,
  restoreAccessToken,
  AUTH_STORAGE_KEY,
} from '../src/services/client.ts';

test('file upload sends actual multipart content without overriding the boundary', async () => {
  clearSessionToken();
  setAccessToken('synthetic-upload-token');
  globalThis.fetch = (async (_url: string, options?: RequestInit) => {
    const headers = new Headers(options?.headers);
    assert.equal(headers.has('Content-Type'), false);
    assert.equal(headers.get('Authorization'), 'Bearer synthetic-upload-token');
    assert.ok(options?.body instanceof FormData);
    const form = options.body as FormData;
    assert.equal(form.get('purpose'), 'MATERIAL');
    assert.equal(await (form.get('file') as File).text(), 'real file content');
    return Response.json({ data: { id: 'uploaded-file' } });
  }) as typeof fetch;
  const uploaded = await uploadFile(new File(['real file content'], 'material.txt'), 'MATERIAL');
  assert.equal(uploaded.id, 'uploaded-file');
  clearSessionToken();
});

test('a transport retry keeps its intent key and session credentials', async () => {
  clearSessionToken();
  const keys: string[] = [];
  let failed = false;
  globalThis.fetch = (async (url: string, options?: RequestInit) => {
    if (url.endsWith('/auth/csrf')) return Response.json({ data: { csrfToken: 'test-token' } });
    assert.equal(options?.credentials, 'omit');
    keys.push(new Headers(options?.headers).get('Idempotency-Key')!);
    assert.match(keys.at(-1)!, /^[0-9a-f-]{36}$/);
    if (!failed) {
      failed = true;
      throw new TypeError('connection lost');
    }
    return Response.json({ data: { id: 'one-result' } });
  }) as typeof fetch;
  await assert.rejects(api('/api/workspaces', 'POST', { title: 'one intent' }), /尚未确认/);
  assert.deepEqual(await api('/api/workspaces', 'POST', { title: 'one intent' }), {
    id: 'one-result',
  });
  assert.equal(keys[0], keys[1]);
});

test('registration sends no Cookie or obsolete CSRF request', async () => {
  clearSessionToken();
  let count = 0;
  globalThis.fetch = (async (url: string, options?: RequestInit) => {
    assert.equal(url, '/api/auth/registrations');
    assert.equal(options?.credentials, 'omit');
    assert.equal(new Headers(options?.headers).has('X-CSRF-Token'), false);
    count++;
    return Response.json({ data: { id: 'registered' } });
  }) as typeof fetch;
  await api('/api/auth/registrations', 'POST', {
    email: 'test@example.com',
    password: '12345',
    username: '测试',
  });
  assert.equal(count, 1);
});

test('JWT survives reload and is removed after expiry or a server rejection', async () => {
  const saved = new Map<string, string>();
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      setItem: (k: string, v: string) => saved.set(k, v),
      getItem: (k: string) => saved.get(k) ?? null,
      removeItem: (k: string) => saved.delete(k),
    },
  });
  clearSessionToken();
  setAccessToken('persisted-token', new Date(Date.now() + 60000).toISOString());
  assert.deepEqual(Object.keys(JSON.parse(saved.get(AUTH_STORAGE_KEY)!)).sort(), [
    'accessToken',
    'expiresAt',
  ]);
  setAccessToken('');
  assert.equal(restoreAccessToken(), true);
  globalThis.fetch = (async (_url: string, options?: RequestInit) => {
    assert.equal(new Headers(options?.headers).get('Authorization'), 'Bearer persisted-token');
    return Response.json(
      { error: { code: 'UNAUTHENTICATED', message: 'expired' } },
      { status: 401 },
    );
  }) as typeof fetch;
  await assert.rejects(api('/api/me'), /expired/);
  assert.equal(saved.has(AUTH_STORAGE_KEY), false);
  saved.set(
    AUTH_STORAGE_KEY,
    JSON.stringify({ accessToken: 'expired-token', expiresAt: '2000-01-01T00:00:00Z' }),
  );
  assert.equal(restoreAccessToken(), false);
  assert.equal(saved.has(AUTH_STORAGE_KEY), false);
});

test('business requests and private previews use the injected Bearer header', async () => {
  clearSessionToken();
  setAccessToken('synthetic-test-token');
  const requests: string[] = [];
  globalThis.fetch = (async (url: string, options?: RequestInit) => {
    const headers = new Headers(options?.headers);
    assert.equal(headers.get('Authorization'), 'Bearer synthetic-test-token');
    assert.equal(headers.has('X-CSRF-Token'), false);
    requests.push(url);
    return Response.json({ data: { id: 'saved' } });
  }) as typeof fetch;
  await api('/api/workspaces', 'POST', { title: 'JWT business call' });
  await authenticatedFetch('/api/resumes/example/preview');
  assert.equal(requests.length, 2);
  clearSessionToken();
});

test('pagination loads every page rather than hiding records after the first twenty', async () => {
  globalThis.fetch = (async (url: string) => {
    const page = Number(new URL(url, 'https://localhost').searchParams.get('page'));
    return Response.json({
      data: { items: page === 1 ? Array.from({ length: 20 }, (_, i) => i) : [20], total: 21 },
    });
  }) as typeof fetch;
  assert.equal((await allPages('/api/resumes')).length, 21);
});

test('backend validation details and request ID are preserved for troubleshooting', async () => {
  globalThis.fetch = (async () =>
    Response.json(
      {
        error: {
          code: 'VALIDATION_ERROR',
          message: 'invalid',
          details: { errors: [{ path: '/document/profile', message: 'missing email' }] },
        },
        requestId: 'trace-test',
      },
      { status: 422 },
    )) as typeof fetch;
  await assert.rejects(api('/api/resumes'), /missing email.*trace-test/);
});


test('public deployment only forwards JWT requests to the configured HTTPS backend', async () => {
  const { backendUrl } = await import('../src/services/client.ts');
  assert.equal(backendUrl('/api/me', 'https://backend.example.com'), 'https://backend.example.com/api/me');
  assert.equal(backendUrl('/internal/files/11111111-1111-4111-8111-111111111111?sig=test', 'https://backend.example.com'), 'https://backend.example.com/internal/files/11111111-1111-4111-8111-111111111111?sig=test');
  assert.equal(backendUrl('/api/me', ''), '/api/me');
  assert.throws(() => backendUrl('https://other.example/api/me', 'https://backend.example.com'));
  assert.throws(() => backendUrl('//other.example/api/me', 'https://backend.example.com'));
  assert.throws(() => backendUrl('/api/me', 'http://backend.example.com'));
});
