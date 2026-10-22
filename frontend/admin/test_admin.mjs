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

test('PW-02 keeps consulted workspace sites and readable entitlement labels', () => {
  assert.match(grants, /displayedGrantSites = new Map\(\)/);
  assert.match(grants, /displayedGrantSites\.set\(site\.id, site\)/);
  assert.match(grants, /await selectGrantSite\(data\.sites\[0\]\)/);
  assert.match(grants, /grantResults\.replaceChildren\(\)/);
  assert.match(grants, /Revocada/);
  assert.match(grants, /Programada/);
  assert.match(grants, /Vencida/);
  assert.match(grants, /Vigente/);
  assert.match(grants, /days\.value = '30'/);
  assert.match(grants, /days\.max = '365'/);
});

test('PW-02 spacing uses page composition while keeping global button styles', async () => {
  const operatorCss = await readFile(new URL('../operator/site-reviews/styles.css', import.meta.url), 'utf8');
  assert.match(styles, /\.admin-grants__search \{ display: grid;/);
  assert.match(styles, /\.admin-grants__form \.admin-grants__field/);
  assert.match(operatorCss, /\.operator-actions button:not\(\.btn\)/);
  assert.match(html, /grants\.js\?v=pw02order372/);
  assert.match(html, /styles\.css\?v=pw02order372/);
});

test('PW-02 dashboard has operator-gated persistent overview and selected site detail', () => {
  assert.match(html, /id="grant-current"/);
  assert.match(html, /id="grant-scheduled"/);
  assert.match(html, /id="grant-historical"/);
  assert.match(html, /id="grant-overview-rows"/);
  assert.match(grants, /api\/access\/operator\/grants\/overview/);
  assert.match(grants, /grantGateObserver\.observe\(grantAdminOperations/);
  assert.match(grants, /grantAdminOperations\.hidden/);
  assert.match(grants, /Este sitio no tiene accesos registrados/);
  assert.match(grants, /Extender cortesía/);
  assert.match(grants, /Las fechas definitivas las determina el servidor/);
  assert.match(styles, /\.admin-page \.operator-main \{ max-width: 1160px/);
  assert.match(styles, /@media \(max-width: 760px\)/);
});

test('PW-02 identifies owner email in overview, site selection and confirmation', () => {
  assert.match(html, /Titular \(email\)/);
  assert.match(grants, /item\.owner_emails/);
  assert.match(grants, /site\.owner_emails/);
  assert.match(grants, /Titular:/);
});


test('PW-02 operator and grant scripts use distinct top-level access gate bindings', () => {
  assert.match(operator, /const adminOperations = document\.querySelector/);
  assert.match(grants, /const grantAdminOperations = document\.querySelector/);
  assert.doesNotMatch(grants, /const adminOperations = /);
});


test('PW-02 orders sites and disables extensions for future reservations', () => {
  assert.match(grants, /a\.hostname\.localeCompare\(b\.hostname/);
  assert.match(grants, /a\.workspace_site_id\.localeCompare\(b\.workspace_site_id\)/);
  assert.match(grants, /Vigente: 0, Programada: 1/);
  assert.match(grants, /submit\.disabled = Boolean\(scheduled \|\| indefinite\)/);
  assert.match(grants, /grantNotice\.textContent = scheduled/);
  assert.match(grants, /if \(submit\.disabled\) return/);
  assert.match(grants, /if \(conflict\) await refresh\(\)/);
});
