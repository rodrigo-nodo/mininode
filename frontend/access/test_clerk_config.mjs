import assert from 'node:assert/strict';
import test from 'node:test';

import { onRequestGet } from '../functions/clerk-config.js';

const request = (host) => new Request('https://' + host + '/clerk-config');

test('production host rejects a development Clerk publishable key', async () => {
  const response = await onRequestGet({
    request: request('app.mininode.io'),
    env: { CLERK_PUBLISHABLE_KEY: 'pk_test_example' },
  });
  assert.equal(response.status, 503);
});

test('production host accepts a production Clerk publishable key', async () => {
  const response = await onRequestGet({
    request: request('app.mininode.io'),
    env: { CLERK_PUBLISHABLE_KEY: 'pk_live_example' },
  });
  assert.equal(response.status, 200);
  assert.equal((await response.json()).publishableKey, 'pk_live_example');
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
});

test('missing Clerk configuration fails closed', async () => {
  const response = await onRequestGet({
    request: request('app.mininode.io'),
    env: {},
  });
  assert.equal(response.status, 503);
});
