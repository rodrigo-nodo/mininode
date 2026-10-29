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

test('keeps protected and existing allowlist behavior unchanged', async () => {
  await assertRejected('/api/privacy/correction-plan-orders/order-123/activate', 'POST');
  await assertRejected('/api/privacy/correction-plan-orders', 'GET');
  await assertRejected('/api/privacy/diagnostic-snapshots/123');
  await assertRejected('/api/admin/users');

  const diagnose = await request('/api/privacy/diagnose', 'POST');
  assert.equal(diagnose.response.status, 200);
  assert.equal(diagnose.calls[0].init.headers.get('X-Api-Key'), API_KEY);

  for (const [path, method] of [
    ['/api/privacy/correction-plan-orders', 'POST'],
    ['/api/privacy/correction-plans/ABC123', 'GET'],
    ['/api/privacy/correction-plans/ABC123/check', 'POST'],
    ['/api/privacy/correction-plans', 'POST'],
  ]) await assertRejected(path, method);

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


test('allows only authenticated POST activation preparation and forwards Bearer', async () => {
  const id = '11111111-1111-4111-8111-111111111111';
  const path = `/api/privacy/workspace-sites/${id}/prepare-activation`;
  const ok = await request(path, 'POST', {
    withoutApiKey: true,
    headers: { Authorization: 'Bearer clerk-session-token' },
  });
  assert.equal(ok.response.status, 200);
  assert.equal(ok.calls.length, 1);
  assert.equal(ok.calls[0].url, `https://backend.example/privacy/workspace-sites/${id}/prepare-activation`);
  assert.equal(ok.calls[0].init.headers.get('Authorization'), 'Bearer clerk-session-token');
  assert.equal(ok.calls[0].init.headers.has('X-Api-Key'), false);

  await assertRejected(path, 'GET');
  await assertRejected(path + '/check', 'POST');
});

test('entitlement and plan routes forward Bearer with exact method/path allowlist', async () => {
  const id = '11111111-1111-4111-8111-111111111111';
  for (const [pathname, method] of [
    [`/api/billing/sites/${id}/entitlement`, 'GET'],
    [`/api/privacy/workspace-sites/${id}/plan`, 'POST'],
    [`/api/privacy/workspace-sites/${id}/plan`, 'GET'],
    [`/api/privacy/workspace-sites/${id}/plan/check`, 'POST'],
  ]) {
    const ok = await request(pathname, method, {
      withoutApiKey: true,
      headers: { Authorization: 'Bearer clerk-session-token' },
    });
    assert.equal(ok.response.status, 200);
    assert.equal(ok.calls.length, 1);
    assert.equal(ok.calls[0].init.headers.get('Authorization'), 'Bearer clerk-session-token');
    assert.equal(ok.calls[0].init.headers.has('X-Api-Key'), false);
  }
  await assertRejected(`/api/billing/sites/${id}/entitlement`, 'POST');
  await assertRejected(`/api/privacy/workspace-sites/${id}/plan/check`, 'GET');
  await assertRejected(`/api/privacy/workspace-sites/${id}/plan/check/extra`, 'POST');
  await assertRejected(`/api/privacy/workspace-sites/${id}/plan`, 'DELETE');
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


test('operator review routes only forward strict authenticated read and decisions', async () => {
  const review = 'df608838-4efc-44e5-8d9c-c1eef6bbb940';
  const route = '/api/access/operator/site-group-reviews';
  const decide = `${route}/${review}/decision`;
  for (const [url, method] of [[route, 'GET'], [decide, 'POST']]) {
    const response = await request(url, method, {
      withoutApiKey: true, headers: { Authorization: 'Bearer operator-session' },
    });
    assert.equal(response.response.status, 200);
    assert.equal(response.calls.length, 1);
    assert.equal(response.calls[0].init.headers.get('Authorization'), 'Bearer operator-session');
    assert.equal(response.calls[0].init.headers.has('X-Api-Key'), false);
  }
  for (const method of ['POST', 'PATCH', 'DELETE']) await assertRejected(route, method);
  for (const method of ['GET', 'PATCH', 'DELETE']) await assertRejected(decide, method);
  await assertRejected(decide + '/extra', 'POST');
  await assertRejected(route + '/all/decision', 'POST');
  await assertRejected('/api/access/operator/members', 'GET');
});


test('PW-02 overview forwards only authenticated GET; other methods and paths remain blocked', async () => {
  const route = '/api/access/operator/grants/overview';
  const token = 'operator-session-token';
  const success = await request(route, 'GET', {
    withoutApiKey: true,
    headers: { Authorization: 'Bearer ' + token },
  });
  assert.equal(success.response.status, 200);
  assert.equal(success.calls.length, 1);
  assert.equal(success.calls[0].url, 'https://backend.example/access/operator/grants/overview');
  assert.equal(success.calls[0].init.headers.get('Authorization'), 'Bearer ' + token);
  assert.equal(success.calls[0].init.headers.has('X-Api-Key'), false);
  for (const method of ['POST', 'PUT', 'PATCH', 'DELETE']) await assertRejected(route, method);
  await assertRejected(route + '/extra', 'GET');
});

test('PW-02 overview route exists consistently in client, API, and proxy', async () => {
  const grants = await readFile(new URL('../../admin/grants.js', import.meta.url), 'utf8');
  const backend = await readFile(new URL('../../../backend/src/mininode_api/api/access.py', import.meta.url), 'utf8');
  assert.ok(grants.includes("'/api/access/operator/grants/overview'"));
  assert.ok(backend.includes('@router.get("/operator/grants/overview")'));
  assert.ok(source.includes("destPathPublic === 'access/operator/grants/overview'"));
});
