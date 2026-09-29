import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const html = await readFile(new URL('./index.html', import.meta.url), 'utf8');
const app = await readFile(new URL('./app.js', import.meta.url), 'utf8');
const root = await readFile(new URL('../index.html', import.meta.url), 'utf8');

test('loads Clerk browser SDK with only the publishable key', () => {
  assert.match(html, /@clerk\/ui@1\/dist\/ui\.browser\.js/);
  assert.match(html, /@clerk\/clerk-js@6\/dist\/clerk\.browser\.js/);
  assert.match(html, /data-clerk-publishable-key="pk_test_/);
  assert.doesNotMatch(html + app, /sk_(?:test|live)_/);
});

test('keeps the Mininode access flow passwordless and privacy-visible', () => {
  assert.match(html, /No necesitas crear una contraseña/);
  assert.match(html, /Google o recibir un código por correo/);
  assert.match(html, /href="\/legal\/privacy\/"/);
  assert.match(app, /elevation: 'flush'/);
  assert.match(app, /socialButtonsPlacement: 'top'/);
  assert.match(app, /withSignUp: true/);
});

test('builds the authenticated home from Access instead of client supplied ownership', () => {
  assert.match(app, /api\('\/api\/access\/me'\)/);
  assert.match(app, /api\('\/api\/access\/context'\)/);
  assert.match(app, /api\('\/api\/access\/onboarding', \{ method: 'POST' \}\)/);
  assert.match(app, /\/api\/access\/workspaces\/\$\{activeWorkspaceId\}\/sites/);
  assert.match(app, /Clerk\.session\?\.getToken\(\)/);
  assert.match(app, /Authorization: `Bearer \\$\{token\}`/);
  assert.doesNotMatch(app, /X-Api-Key/);
});

test('organizes account navigation by product and nests product resources', () => {
  assert.match(html, /<h2>Privacy Web<\/h2>/);
  assert.match(html, /<h3>Mis sitios<\/h3>/);
  assert.match(html, /\+ Agregar sitio/);
  assert.match(html, /<h2>Privacy Data<\/h2>/);
  assert.match(html, /<h3>Mapas<\/h3>/);
  assert.match(html, /Próximamente/);
  assert.doesNotMatch(html, /<h2>Mis sitios<\/h2>/);
});

test('app.mininode.io root redirects into the access experience', () => {
  assert.match(root, /window\.location\.hostname === 'app\.mininode\.io'/);
  assert.match(root, /window\.location\.replace\('\/access\/'\)/);
});


test('offers explicit recovery when an existing Clerk session is rejected', () => {
  assert.match(app, /Tu sesión ya no puede validarse\. Cierra la sesión y vuelve a acceder\./);
  assert.match(app, /setVisible\(errorSignOutButton, Boolean\(Clerk\.session\)\)/);
  assert.match(html, /id="access-error-sign-out"/);
});


test('visibility helper tolerates optional UI elements', () => {
  assert.match(app, /function setVisible\(element, visible\) \{[\s\S]*if \(!element\) return;[\s\S]*element\.hidden = !visible;/);
});


test('refreshes the Clerk token for every authenticated API request', () => {
  assert.match(app, /async function api\(path, options = \{\}\) \{[\s\S]*Clerk\.session\?\.getToken\(\)[\s\S]*Authorization: `Bearer \$\{token\}`/);
  assert.doesNotMatch(app, /let accessToken/);
});
