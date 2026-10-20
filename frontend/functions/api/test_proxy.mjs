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
    return new Response(options.upstreamStatus === 204 ? null : JSON.stringify({ ok: true }), {
      status: options.upstreamStatus || 200,
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
    return { response, json: response.status === 204 ? null : await response.json(), calls };
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


test('allows only GET for Access identity and forwards the Cloudflare assertion', async () => {
  const result = await request('/api/access/me', 'GET', {
    withoutApiKey: true,
    headers: { 'Cf-Access-Jwt-Assertion': 'signed-access-token' },
  });

  assert.equal(result.response.status, 200);
  assert.equal(result.calls.length, 1);
  assert.equal(result.calls[0].url, 'https://backend.example/access/me');
  assert.equal(result.calls[0].init.method, 'GET');
  assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);
  assert.equal(
    result.calls[0].init.headers.get('Cf-Access-Jwt-Assertion'),
    'signed-access-token',
  );

  for (const method of ['POST', 'PATCH', 'DELETE', 'PUT']) {
    await assertRejected('/api/access/me', method);
  }
});


test('allows only GET for Access context and forwards the Cloudflare assertion', async () => {
  const result = await request('/api/access/context', 'GET', {
    withoutApiKey: true,
    headers: { 'Cf-Access-Jwt-Assertion': 'signed-access-token' },
  });

  assert.equal(result.response.status, 200);
  assert.equal(result.calls.length, 1);
  assert.equal(result.calls[0].url, 'https://backend.example/access/context');
  assert.equal(result.calls[0].init.method, 'GET');
  assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);
  assert.equal(
    result.calls[0].init.headers.get('Cf-Access-Jwt-Assertion'),
    'signed-access-token',
  );

  for (const method of ['POST', 'PATCH', 'DELETE', 'PUT']) {
    await assertRejected('/api/access/context', method);
  }
});


test('forwards Clerk bearer token only on protected Access routes', async () => {
  const token = 'clerk-session-token';
  const accessResult = await request('/api/access/me', 'GET', {
    withoutApiKey: true,
    headers: { Authorization: `Bearer ${token}` },
  });

  assert.equal(accessResult.response.status, 200);
  assert.equal(accessResult.calls.length, 1);
  assert.equal(
    accessResult.calls[0].init.headers.get('Authorization'),
    `Bearer ${token}`,
  );
  assert.equal(accessResult.calls[0].init.headers.has('X-Api-Key'), false);

  const publicResult = await request('/api/privacy/diagnose', 'POST', {
    headers: { Authorization: `Bearer ${token}` },
  });
  assert.equal(publicResult.response.status, 200);
  assert.equal(publicResult.calls[0].init.headers.has('Authorization'), false);
  assert.equal(publicResult.calls[0].init.headers.get('X-Api-Key'), API_KEY);
});


test('forwards Clerk bearer token to authenticated Privacy Web diagnosis', async () => {
  const id = '11111111-1111-4111-8111-111111111111';
  const result = await request(`/api/privacy/workspace-sites/${id}/diagnose`, 'POST', {
    withoutApiKey: true,
    headers: { Authorization: 'Bearer clerk-session-token' },
  });
  assert.equal(result.response.status, 200);
  assert.equal(result.calls.length, 1);
  assert.equal(result.calls[0].url, `https://backend.example/privacy/workspace-sites/${id}/diagnose`);
  assert.equal(result.calls[0].init.headers.get('Authorization'), 'Bearer clerk-session-token');
  assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);
});


test('forwards Clerk bearer token to workspace URL Privacy diagnosis', async () => {
  const id = '22222222-2222-4222-8222-222222222222';
  const result = await request(`/api/privacy/workspaces/${id}/diagnose`, 'POST', {
    withoutApiKey: true,
    headers: { Authorization: 'Bearer clerk-session-token' },
  });
  assert.equal(result.response.status, 200);
  assert.equal(result.calls.length, 1);
  assert.equal(result.calls[0].url, `https://backend.example/privacy/workspaces/${id}/diagnose`);
  assert.equal(result.calls[0].init.headers.get('Authorization'), 'Bearer clerk-session-token');
  assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);

  await assertRejected(`/api/privacy/workspaces/${id}/diagnose`, 'GET');
});


test('forwards Clerk bearer token to latest Privacy review reads', async () => {
  const siteId = '33333333-3333-4333-8333-333333333333';
  const workspaceId = '44444444-4444-4444-8444-444444444444';

  const latest = await request(`/api/privacy/workspace-sites/${siteId}/latest-review`, 'GET', {
    withoutApiKey: true,
    headers: { Authorization: 'Bearer clerk-session-token' },
  });
  assert.equal(latest.response.status, 200);
  assert.equal(latest.calls[0].url, `https://backend.example/privacy/workspace-sites/${siteId}/latest-review`);
  assert.equal(latest.calls[0].init.headers.get('Authorization'), 'Bearer clerk-session-token');
  assert.equal(latest.calls[0].init.headers.has('X-Api-Key'), false);

  const summaries = await request(`/api/privacy/workspaces/${workspaceId}/latest-reviews`, 'GET', {
    withoutApiKey: true,
    headers: { Authorization: 'Bearer clerk-session-token' },
  });
  assert.equal(summaries.response.status, 200);
  assert.equal(summaries.calls[0].url, `https://backend.example/privacy/workspaces/${workspaceId}/latest-reviews`);
  assert.equal(summaries.calls[0].init.headers.get('Authorization'), 'Bearer clerk-session-token');
  assert.equal(summaries.calls[0].init.headers.has('X-Api-Key'), false);

  await assertRejected(`/api/privacy/workspace-sites/${siteId}/latest-review`, 'POST');
  await assertRejected(`/api/privacy/workspaces/${workspaceId}/latest-reviews`, 'POST');
});

test('only DELETE on exact authorized workspace-site path is proxied with bearer and empty 204', async () => {
  const workspace = 'e09cf07b-2f3d-4a8a-9519-203b7bb6aa13';
  const site = 'cc285ffb-ab8a-4c5e-b333-76b9f7af224f';
  const path = `/api/access/workspaces/${workspace}/sites/${site}`;
  const result = await request(path, 'DELETE', {
    withoutApiKey: true,
    upstreamStatus: 204,
    headers: { Authorization: 'Bearer session-token' },
  });
  assert.equal(result.response.status, 204);
  assert.equal(await result.response.text(), '');
  assert.equal(result.calls.length, 1);
  assert.equal(result.calls[0].init.method, 'DELETE');
  assert.equal(result.calls[0].url, `https://backend.example/access/workspaces/${workspace}/sites/${site}`);
  assert.equal(result.calls[0].init.headers.get('Authorization'), 'Bearer session-token');
  assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);
  for (const method of ['GET', 'POST', 'PATCH']) await assertRejected(path, method);
  await assertRejected(path + '/other', 'DELETE');
  await assertRejected('/api/access/workspaces/' + workspace + '/sites/', 'DELETE');
});

test('accepts only POST on protected unlink action and forwards Clerk bearer', async () => {
  const workspace = 'e09cf07b-2f3d-4a8a-9519-203b7bb6aa13';
  const site = 'cc285ffb-ab8a-4c5e-b333-76b9f7af224f';
  const route = `/api/access/workspaces/${workspace}/sites/${site}/unlink`;
  const response = await request(route, 'POST', {
    withoutApiKey: true,
    upstreamStatus: 204,
    headers: { Authorization: 'Bearer valid-clerk-session' },
  });
  assert.equal(response.response.status, 204);
  assert.equal(response.json, null);
  assert.equal(response.calls.length, 1);
  assert.equal(response.calls[0].url, `https://backend.example/access/workspaces/${workspace}/sites/${site}/unlink`);
  assert.equal(response.calls[0].init.method, 'POST');
  assert.equal(response.calls[0].init.headers.get('Authorization'), 'Bearer valid-clerk-session');
  assert.equal(response.calls[0].init.headers.has('X-Api-Key'), false);
  for (const method of ['GET', 'PATCH', 'DELETE', 'PUT']) await assertRejected(route, method);
  await assertRejected(route + '/anything', 'POST');
  await assertRejected(route.replace('/unlink', '/other'), 'POST');
});


test('site grouping review queue forwards only authenticated GET and POST', async () => {
  const workspace = 'e09cf07b-2f3d-4a8a-9519-203b7bb6aa13';
  const route = `/api/access/workspaces/${workspace}/site-group-reviews`;
  for (const method of ['GET', 'POST']) {
    const result = await request(route, method, {
      withoutApiKey: true, headers: { Authorization: 'Bearer protected-session' },
    });
    assert.equal(result.response.status, 200);
    assert.equal(result.calls.length, 1);
    assert.equal(result.calls[0].init.headers.get('Authorization'), 'Bearer protected-session');
    assert.equal(result.calls[0].init.headers.has('X-Api-Key'), false);
  }
  for (const method of ['PATCH', 'DELETE', 'PUT']) await assertRejected(route, method);
  await assertRejected(route + '/approve', 'POST');
  await assertRejected(route.replace(workspace, 'foreign'), 'POST');
});
