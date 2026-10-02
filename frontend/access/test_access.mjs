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
  assert.doesNotMatch(html, /\+ Agregar sitio/);
  assert.match(html, /Aún no has realizado revisiones\./);
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
  assert.match(coreAuth, /#header-account-menu/);
  assert.match(coreAuth, /#header-sign-out/);
  assert.match(coreAuth, /accessControl\.hidden = signedIn/);
  assert.match(coreAuth, /accountMenu\.hidden = !signedIn/);
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
  const makeElement = () => ({
    dataset: {},
    hidden: false,
    textContent: '',
    title: '',
    attributes: new Map(),
    setAttribute(name, value) { this.attributes.set(name, value); },
    removeAttribute(name) {
      this.attributes.delete(name);
      if (name === 'title') this.title = '';
      if (name === 'open') this.open = false;
    },
    addEventListener(name, listener) { listeners.set(name, listener); },
  });
  const accessControl = makeElement();
  const accountMenu = makeElement();
  const signOutControl = makeElement();
  const email = makeElement();
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
      querySelector(selector) {
        if (selector === '#header-auth-control') return accessControl;
        if (selector === '#header-account-menu') return accountMenu;
        if (selector === '#header-sign-out') return signOutControl;
        if (selector === '#header-account-email') return email;
        return null;
      },
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

  await listeners.get('click')();

  assert.equal(redirectedTo, null);
  assert.equal(signOutControl.textContent, 'Reintentar cierre');
  assert.equal(signOutControl.attributes.get('aria-label'), 'No se pudo cerrar sesión. Intenta nuevamente.');
});


test('successful global sign-out returns to the identification screen', async () => {
  const listeners = new Map();
  let redirectedTo = null;
  const signOutControl = {
    dataset: {}, hidden: false, textContent: '',
    setAttribute() {}, removeAttribute() {},
    addEventListener(name, listener) { listeners.set(name, listener); },
  };
  const context = {
    window: {
      location: { hostname: 'app.mininode.io', assign(url) { redirectedTo = url; } },
      addEventListener() {}, dispatchEvent() {},
    },
    document: {
      body: { dataset: { mininodeAuthUi: 'clerk' } },
      documentElement: {}, scripts: [],
      querySelector(selector) {
        return selector === '#header-sign-out' ? signOutControl : null;
      },
    },
    MutationObserver: class {
      constructor(callback) { this.callback = callback; }
      observe() { this.callback(); }
      disconnect() {}
    },
    CustomEvent: class { constructor(type) { this.type = type; } },
    console, Set,
  };
  context.window.window = context.window;
  context.window.document = context.document;
  vm.runInNewContext(coreAuth, context);
  context.window.MininodeAuth.isSignedIn = () => true;
  let providerSignedOut = false;
  context.window.MininodeAuth.signOut = async () => { providerSignedOut = true; };
  await listeners.get('click')();
  assert.equal(providerSignedOut, true);
  assert.equal(redirectedTo, '/access/');
});

test('workspace selector stays hidden for one workspace and appears only for multiple', () => {
  assert.match(html, /id="workspace-picker-label" class="workspace-picker" hidden/);
  assert.match(app, /setVisible\(workspacePickerLabel, workspaces\.length > 1\)/);
});

test('account home does not expose manual site creation', () => {
  assert.doesNotMatch(html, /id="site-add-open"/);
  assert.doesNotMatch(html, /id="site-add-form"/);
  assert.doesNotMatch(app, /siteAddOpen/);
  assert.doesNotMatch(app, /siteAddForm/);
  assert.doesNotMatch(app, /\/api\/access\/workspaces\/\$\{activeWorkspaceId\}\/sites/);
});


test('Privacy Web opens with the active workspace context', () => {
  assert.match(html, /id="privacy-web-open"/);
  assert.match(app, /privacyWebOpen\.href = `\/privacy\/\?workspace_id=\$\{encodeURIComponent\(active\.id\)\}`/);
});


test('formats latest review date with Chile time', () => {
  assert.match(app, /timeZone: 'America\/Santiago'/);
  assert.match(app, /hour: '2-digit'/);
  assert.match(app, /minute: '2-digit'/);
  assert.match(app, /hour12: false/);
});

test('account shows the latest Privacy Web review for each site', () => {
  assert.match(app, /\/api\/privacy\/workspaces\/\$\{encodeURIComponent\(workspace\.id\)\}\/latest-reviews/);
  assert.match(app, /Última revisión: \$\{formattedDate\}/);
  assert.match(app, /pieces\.push\(\`\$\{review\.score\}\/100\`\)/);
  assert.match(app, /view=latest/);
  assert.match(app, /Ver resultado →/);
  assert.match(app, /site-review-meta/);
});
