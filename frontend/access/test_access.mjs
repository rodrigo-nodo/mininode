import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const html = await readFile(new URL('./index.html', import.meta.url), 'utf8');
const app = await readFile(new URL('./app.js', import.meta.url), 'utf8');
const root = await readFile(new URL('../index.html', import.meta.url), 'utf8');
const styles = await readFile(new URL('./styles.css', import.meta.url), 'utf8');

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
  assert.match(app, /socialButtonsPlacement: 'top'/);
  assert.match(app, /lastAuthenticationStrategyBadge: \{ display: 'none' \}/);
  assert.match(app, /withSignUp: true/);
});

test('exchanges the Clerk session token only with the Access identity endpoint', () => {
  assert.match(app, /session\.getToken\(\)/);
  assert.match(app, /fetch\('\/api\/access\/me'/);
  assert.match(app, /Authorization: `Bearer \$\{token\}`/);
  assert.doesNotMatch(app, /X-Api-Key/);
});

test('app.mininode.io root redirects into the access experience', () => {
  assert.match(root, /window\.location\.hostname === 'app\.mininode\.io'/);
  assert.match(root, /window\.location\.replace\('\/access\/'\)/);
});
