import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const html = await readFile(new URL('./index.html', import.meta.url), 'utf8');
const app = await readFile(new URL('./app.js', import.meta.url), 'utf8');

test('operator panel has no hardcoded credentials or public approval links', () => {
  assert.match(html, /Solicitudes de agrupación/);
  assert.match(html, /noindex,nofollow/);
  assert.doesNotMatch(app, /innerHTML|localStorage|sessionStorage/);
  assert.match(app, /auth\.getToken\(\)/);
  assert.match(app, /Authorization: `Bearer \$\{token\}`/);
  assert.match(app, /\/api\/access\/operator\/site-group-reviews/);
  assert.match(app, /decision: action, note/);
  assert.match(app, /window\.confirm/);
  assert.match(app, /item\.status !== 'pending'/);
});
