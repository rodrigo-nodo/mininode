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
  assert.match(html, /id="admin-operations" hidden/);
  assert.match(operator, /if \(adminOperations\) adminOperations\.hidden = false/);
  assert.match(operator, /Acceso restringido/);
  assert.match(html, /operator\/site-reviews\/app\.js/);
  assert.match(operator, /auth\.getToken\(\)/);
  assert.match(operator, /\/api\/access\/operator\/site-group-reviews/);
  assert.match(operator, /decision: action, note/);
  assert.doesNotMatch(html, /accessos gratuitos|Habilitar acceso/i);
});

const grants = await readFile(new URL('./grants.js', import.meta.url), 'utf8');
const styles = await readFile(new URL('./styles.css', import.meta.url), 'utf8');

test('Admin search adopts global controls and removes literal newline', () => {
  assert.match(html, /URL del sitio web/);
  assert.match(html, /placeholder="https:\/\/tusitio\.cl"/);
  assert.match(html, /class="form-control"/);
  assert.match(html, /class="form-field admin-grants__field"/);
  assert.match(html, /class="btn btn--secondary"/);
  assert.equal(html.includes(String.raw`\n        <form`), false);
  assert.doesNotMatch(styles, /\.admin-grants__field input\s*\{/);
  assert.match(grants, /input\.classList\.add\('form-control'\)/);
});

test('Admin normalizes URL to hostname and preserves workspace-specific actions', () => {
  assert.match(grants, /new URL\(candidate\)\.hostname\.toLowerCase\(\)/);
  assert.match(grants, /encodeURIComponent\(normalizeGrantSearch\(grantSearch\.value\)\)/);
  assert.match(grants, /site\.workspace/);
  assert.match(grants, /workspace_site_id: site\.id/);
});
