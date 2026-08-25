import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const routePath = new URL('../../functions/privacy/plan/[token].js', import.meta.url);
const routeSource = await readFile(routePath, 'utf8');
const routeModule = await import(`data:text/javascript,${encodeURIComponent(routeSource)}`);

const runRoute = async (pathname) => {
  const request = new Request(`https://mininode.io${pathname}?do-not-forward=1`);
  const calls = [];
  const response = await routeModule.onRequest({
    request,
    env: {
      ASSETS: {
        fetch: async (input) => {
          calls.push(input);
          return new Response('Plan de corrección de privacidad', { status: 200 });
        },
      },
    },
  });
  return { request, calls, response };
};

for (const pathname of [
  '/privacy/plan/ABC123',
  '/privacy/plan/ABC123/',
  '/privacy/plan/Az_09-token',
]) {
  const { calls, response } = await runRoute(pathname);
  assert.equal(response.status, 200);
  assert.equal(calls.length, 1);
  assert.equal(new URL(calls[0]).pathname, '/privacy/plan/');
  assert.equal(new URL(calls[0]).search, '');
  assert.equal(response.headers.get('location'), null);
}

for (const pathname of [
  '/privacy/plan/',
  '/privacy/',
  '/privacy/plan-demo/',
  '/privacy/data/',
  '/privacy/plan/foo/bar',
  '/privacy/plan/index.html/extra',
]) {
  const { request, calls } = await runRoute(pathname);
  assert.equal(calls.length, 1);
  assert.strictEqual(calls[0], request);
}
