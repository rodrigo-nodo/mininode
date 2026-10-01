import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const html = await readFile(new URL('./index.html', import.meta.url), 'utf8');
const app = await readFile(new URL('./app.js', import.meta.url), 'utf8');
const root = await readFile(new URL('../index.html', import.meta.url), 'utf8');
const coreAuth = await readFile(new URL('../assets/js/core-auth.js', import.meta.url), 'utf8');

test('loads identity runtime only from shared MininodeAuth', () => {
  assert.doesNotMatch(html, /clerk\.accounts\.dev/);
  assert.doesNotMatch(html, /data-clerk-publishable-key="pk_(?:test|live)_/);
  assert.match(coreAuth, /fetch\('\/clerk-config'/);
  assert.match(coreAuth, /@clerk\/ui@1\/dist\/ui\.browser\.js/);
  assert.match(coreAuth, /@clerk\/clerk-js@6\/dist\/clerk\.browser\.js/);
  assert.match(coreAuth, /app\.mininode\.io/);
  assert.match(coreAuth, /publishableKey\.startsWith\('pk_live_'\)/);
  assert.match(coreAuth, /window\.MininodeAuth = api/);
  assert.doesNotMatch(app, /fetch\('\/clerk-config'/);
  assert.doesNotMatch(app, /@clerk\//);
  assert.doesNotMatch(app, /(?:window\.)?Clerk\./);
  assert.doesNotMatch(html + app + coreAuth, /sk_(?:test|live)_/);
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
  assert.match(app, /mininodeAuth\.getToken\(\)/);
  assert.match(app, /Authorization: `Bearer \$\{token\}`/);
  assert.doesNotMatch(app, /X-Api-Key/);
});

test('organizes account navigation by product and nests product resources', () => {
  assert.match(html, /<h2>Privacy Web<\/h2>/);
  assert.match(html, /data-include="\.\.\/partials\/footer\.html"/);
  assert.match(html, /data-include="\.\.\/partials\/header-nav\.html"/);
  assert.doesNotMatch(html, /<h1 id="account-title">Mi espacio<\/h1>/);
  assert.doesNotMatch(html, /id="account-email"/);
  assert.doesNotMatch(html, /mininode-favicon\.svg/);
  assert.match(app, /\/privacy\/\?workspace_site_id=\$\{encodeURIComponent\(site\.id\)\}/);
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
  assert.match(app, /setVisible\(errorSignOutButton, hasSession\)/);
  assert.match(html, /id="access-error-sign-out"/);
});


test('visibility helper tolerates optional UI elements', () => {
  assert.match(app, /function setVisible\(element, visible\) \{[\s\S]*if \(!element\) return;[\s\S]*element\.hidden = !visible;/);
});


test('refreshes the identity token through MininodeAuth for every authenticated API request', () => {
  assert.match(app, /async function api\(path, options = \{\}\) \{[\s\S]*mininodeAuth\.getToken\(\)[\s\S]*Authorization: `Bearer \$\{token\}`/);
  assert.doesNotMatch(app, /let accessToken/);
});


test('shared header session state is owned by MininodeAuth', () => {
  assert.doesNotMatch(app, /#header-sign-out/);
  assert.doesNotMatch(app, /#header-access-link/);
  assert.doesNotMatch(app, /#header-auth-control/);
  assert.match(coreAuth, /#header-auth-control/);
  assert.match(coreAuth, /control\.textContent = signedIn \? 'Cerrar sesión' : 'Acceder'/);
});


test('access does not own global sign-out binding', () => {
  assert.doesNotMatch(app, /signOutButton/);
  assert.doesNotMatch(app, /syncHeaderControls/);
  assert.match(coreAuth, /dataset\.authBound/);
  assert.match(coreAuth, /api\.signOut\(\)/);
});


test('waits for the shared MininodeAuth API instead of bootstrapping identity locally', () => {
  assert.match(app, /waitForMininodeAuth/);
  assert.match(app, /mininode:auth-api-ready/);
  assert.match(app, /mininodeAuth\.ready\(\{ ui: true, localization \}\)/);
  assert.doesNotMatch(app, /loadClerkRuntime/);
  assert.doesNotMatch(app, /loadExternalScript/);
});


test('global sign-out failure keeps the user on the current page and exposes retry state', async () => {
  const listeners = new Map();
  const control = {
    dataset: {},
    textContent: '',
    title: '',
    attributes: new Map(),
    setAttribute(name, value) { this.attributes.set(name, value); },
    removeAttribute(name) { this.attributes.delete(name); if (name === 'title') this.title = ''; },
    addEventListener(name, listener) { listeners.set(name, listener); },
  };
  let redirectedTo = null;
  const context = {
    window: {
      location: { hostname: 'dev.mininode.io', assign(url) { redirectedTo = url; } },
      addEventListener() {},
      dispatchEvent() {},
    },
    document: {
      body: { dataset: { mininodeAuthUi: 'clerk' } },
      documentElement: {},
      scripts: [],
      querySelector(selector) { return selector === '#header-auth-control' ? control : null; },
    },
    MutationObserver: class {
      constructor(callback) { this.callback = callback; }
      observe() { this.callback(); }
      disconnect() {}
    },
    CustomEvent: class { constructor(type) { this.type = type; } },
    console,
    Set,
  };
  context.window.window = context.window;
  context.window.document = context.document;
  vm.runInNewContext(coreAuth, context);

  context.window.MininodeAuth.isSignedIn = () => true;
  context.window.MininodeAuth.signOut = async () => { throw new Error('provider unavailable'); };

  let prevented = false;
  await listeners.get('click')({ preventDefault() { prevented = true; } });

  assert.equal(prevented, true);
  assert.equal(redirectedTo, null);
  assert.equal(control.textContent, 'Reintentar cierre');
  assert.equal(control.attributes.get('aria-label'), 'No se pudo cerrar sesión. Intenta nuevamente.');
});
