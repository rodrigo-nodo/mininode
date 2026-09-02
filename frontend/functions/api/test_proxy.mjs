import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(new URL('./[[path]].js', import.meta.url), 'utf8');
const { onRequest } = await import(`data:text/javascript,${encodeURIComponent(source)}`);

const API_KEY = 'server-only-secret';

async function request(path, method = 'GET', options = {}) {
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const headers = options.headers || {};
    const body = ['GET', 'HEAD'].includes(method) ? undefined : '{}';
    const context = {
      request: new Request(`https://mininode.io${path}`, { method, headers, body }),
      env: {
        MININODE_API_BASE: 'https://backend.example',
        ...(!options.withoutApiKey && { MININODE_API_KEY: API_KEY }),
      },
    };
    if (Object.hasOwn(options, 'params')) context.params = options.params;
    const response = await onRequest(context);
    return { response, json: await response.json(), calls };
  } finally {
    globalThis.fetch = originalFetch;
  }
}

async function assertRejected(path, method = 'GET') {
  const result = await request(path, method);
  assert.equal(result.response.status, 403);
  assert.equal(result.json.error, 'Path no permitido');
  assert.equal(result.calls.length, 0);
}

test('allows strict public correction-plan reads and forwards query strings', async () => {
  const tokens = [
    'ABC123',
    'PLAN-003',
    'Upper_lower-0123456789',
    'GlHIycPAQYtNNOSz9hYKz_8u4-jbH6PpN3wRZsT0aVq7CdEfLmX2',
  ];

  for (const [index, token] of tokens.entries()) {
    const result = await request(`/api/privacy/correction-plans/${token}?v=2`, 'GET', {
      withoutApiKey: index === 0,
    });
    assert.equal(result.response.status, 200);
    assert.equal(result.calls.length, 1);
    assert.equal(result.calls[0].url, `https://backend.example/privacy/correction-plans/${token}?v=2`);
    assert.equal(result.calls[0].init.method, 'GET');
    assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);
    assert.equal(JSON.stringify(result.json).includes(API_KEY), false);
  }
});

test('uses request pathname regardless of catch-all params representation', async () => {
  const paramsVariants = [
    undefined,
    {},
    { path: 'privacy/correction-plans/ABC123' },
    { path: ['privacy', 'correction-plans', 'ABC123'] },
    { path: { unexpected: true } },
  ];

  for (const params of paramsVariants) {
    const result = await request('/api/privacy/correction-plans/ABC123', 'GET', {
      withoutApiKey: true,
      params,
    });
    assert.equal(result.response.status, 200);
    assert.equal(result.calls[0].url, 'https://backend.example/privacy/correction-plans/ABC123');
  }
});

test('normalizes an optional trailing slash before forwarding public plan routes', async () => {
  const read = await request('/api/privacy/correction-plans/ABC123/', 'GET', { withoutApiKey: true });
  assert.equal(read.response.status, 200);
  assert.equal(read.calls[0].url, 'https://backend.example/privacy/correction-plans/ABC123');

  const check = await request('/api/privacy/correction-plans/ABC123/check/', 'POST', { withoutApiKey: true });
  assert.equal(check.response.status, 200);
  assert.equal(check.calls[0].url, 'https://backend.example/privacy/correction-plans/ABC123/check');
});

test('allows only POST for the public correction-plan check', async () => {
  const result = await request('/api/privacy/correction-plans/ABC123/check', 'POST', { withoutApiKey: true });
  assert.equal(result.response.status, 200);
  assert.equal(result.calls[0].url, 'https://backend.example/privacy/correction-plans/ABC123/check');
  assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);

  await assertRejected('/api/privacy/correction-plans/ABC123', 'POST');
  await assertRejected('/api/privacy/correction-plans/ABC123/check', 'GET');
  for (const method of ['PUT', 'PATCH', 'DELETE']) {
    await assertRejected('/api/privacy/correction-plans/ABC123', method);
  }
});

test('rejects malformed tokens, traversal, and additional segments', async () => {
  for (const path of [
    '/api/privacy/correction-plans/',
    '/api/privacy/correction-plans/foo/bar',
    '/api/privacy/correction-plans/foo/check/bar',
    '/api/privacy/correction-plans/../foo',
    '/api/privacy/correction-plans/%2Ffoo',
    '/api/privacy/correction-plans/foo/extra',
  ]) {
    await assertRejected(path);
  }
});

test('keeps protected and existing allowlist behavior unchanged', async () => {
  await assertRejected('/api/privacy/correction-plan-orders/order-123/activate', 'POST');
  await assertRejected('/api/privacy/correction-plan-orders', 'GET');
  await assertRejected('/api/privacy/diagnostic-snapshots/123');
  await assertRejected('/api/admin/users');

  const diagnose = await request('/api/privacy/diagnose', 'POST');
  assert.equal(diagnose.response.status, 200);
  assert.equal(diagnose.calls[0].init.headers.get('X-Api-Key'), API_KEY);

  const order = await request('/api/privacy/correction-plan-orders', 'POST');
  assert.equal(order.response.status, 200);
  assert.equal(order.calls[0].init.headers.has('X-Api-Key'), false);

  const missingKey = await request('/api/privacy/diagnose', 'POST', { withoutApiKey: true });
  assert.equal(missingKey.response.status, 500);
  assert.equal(missingKey.json.error, 'Falta MININODE_API_KEY (Pages Secret)');
  assert.equal(missingKey.calls.length, 0);
});

test('allows only GET for Privacy Data map review', async () => {
  const token = 'map_token-123';
  const result = await request(`/api/privacy/data/maps/${token}/review`, 'GET', { withoutApiKey: true });
  assert.equal(result.response.status, 200);
  assert.equal(result.calls.length, 1);
  assert.equal(result.calls[0].url, `https://backend.example/privacy/data/maps/${token}/review`);
  assert.equal(result.calls[0].init.method, 'GET');
  assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);

  for (const method of ['POST', 'PATCH', 'DELETE', 'PUT']) {
    await assertRejected(`/api/privacy/data/maps/${token}/review`, method);
  }
  await assertRejected(`/api/privacy/data/maps/${token}/review/extra`, 'GET');
});
