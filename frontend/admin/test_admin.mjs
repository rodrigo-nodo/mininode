import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const html = await readFile(new URL('./index.html', import.meta.url), 'utf8');
const operator = await readFile(new URL('../operator/site-reviews/app.js', import.meta.url), 'utf8');

test('Mininode Admin is the single Privacy Web admin entry and reuses secured grouping', () => {
  assert.match(html, /<h1 id="admin-title">Mininode Admin<\/h1>/);
  assert.match(html, /Privacy Web/);
  assert.match(html, /Solicitudes de agrupación/);
  assert.match(html, /noindex,nofollow/);
  assert.match(html, /id="operator-status"/);
  assert.match(html, /id="operator-reviews"/);
  assert.match(html, /operator\/site-reviews\/app\.js/);
  assert.match(operator, /auth\.getToken\(\)/);
  assert.match(operator, /\/api\/access\/operator\/site-group-reviews/);
  assert.match(operator, /decision: action, note/);
  assert.doesNotMatch(html, /accessos gratuitos|Habilitar acceso/i);
});
