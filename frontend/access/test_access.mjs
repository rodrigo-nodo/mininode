import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const html = await readFile(new URL('./index.html', import.meta.url), 'utf8');
const app = await readFile(new URL('./app.js', import.meta.url), 'utf8');
const styles = await readFile(new URL('./styles.css', import.meta.url), 'utf8');
const root = await readFile(new URL('../index.html', import.meta.url), 'utf8');
const coreAuth = await readFile(new URL('../assets/js/core-auth.js', import.meta.url), 'utf8');

test('access script URL fingerprints its current contents to prevent stale claim payloads', () => {
  const header = `blob ${Buffer.byteLength(app, 'utf8')}\0`;
  const blobSha = createHash('sha1').update(header).update(app).digest('hex').slice(0, 12);
  assert.ok(html.includes(`./app.js?v=${blobSha}`), 'Access HTML must reference the current JS blob');
  assert.match(app, /No pudimos validar los datos del diagnóstico/);
  assert.doesNotMatch(app, /JSON\.stringify\(\{ \.\.\.claim, workspace_id:/);
});


function freeClaimHarness(intent, { claimFails = false, refreshFails = false } = {}) {
  const key = 'mininode.privacy.pending_claim.v1';
  const values = new Map([[key, JSON.stringify({ diagnostic_id: 'diag-1', claim_token: 'proof', intent })]]);
  const pendingClaimPanel = { hidden: true, querySelector: () => ({ textContent: '' }) };
  const pendingClaimError = { textContent: '', hidden: true };
  const pendingClaimButton = { hidden: true, textContent: '' };
  const claimSuccessPanel = { hidden: true };
  const claimSuccessDescription = { textContent: '' };
  const claimSuccessResult = { href: '' };
  const workspacePicker = { disabled: false };
  const seen = { requests: [], redirects: [], homeRenders: 0 };
  const context = {
    claimInFlight: false,
    pendingClaimPanel, pendingClaimError, pendingClaimButton,
    claimSuccessPanel, claimSuccessDescription, claimSuccessResult, workspacePicker,
    PENDING_CLAIM_KEY: key, activeWorkspaceId: 'workspace-1',
    sessionStorage: {
      getItem: (k) => values.get(k) ?? null,
      removeItem: (k) => values.delete(k),
    },
    window: { location: { assign: (url) => seen.redirects.push(url) } },
    renderHome() { seen.homeRenders += 1; },
    async api(path, options) {
      seen.requests.push({ path, body: options?.body && JSON.parse(options.body) });
      if (path === '/api/privacy/diagnostic-claims') {
        if (claimFails) throw new Error('No pudimos guardar');
        return { diagnostic_id: 'diag-1', workspace_site_id: 'site-1' };
      }
      if (path === '/api/access/context') {
        if (refreshFails) throw new Error('Refresh failed');
        return { workspaces: [{ id: 'workspace-1', sites: [{ id: 'site-1', hostname: 'gurbana.cl' }] }] };
      }
      throw new Error('Unexpected route ' + path);
    },
  };
  const start = app.indexOf('function showSavedDiagnosticConfirmation(');
  const end = app.indexOf("pendingClaimButton.addEventListener('click'", start);
  assert.ok(start >= 0 && end > start);
  vm.runInNewContext(app.slice(start, end) + '\nglobalThis.runClaim = savePendingDiagnostic;', context);
  return { context, values, seen };
}

test('free claim completes inside Mi espacio, refreshes Mis sitios and exposes the saved review', async () => {
  const { context, values, seen } = freeClaimHarness('save');
  await context.runClaim();

  assert.deepEqual(seen.redirects, []);
  assert.equal(values.has('mininode.privacy.pending_claim.v1'), false);
  assert.equal(context.pendingClaimPanel.hidden, true);
  assert.equal(context.claimSuccessPanel.hidden, false);
  assert.match(context.claimSuccessDescription.textContent, /gurbana\.cl/);
  assert.equal(context.claimSuccessResult.href, '/privacy/?workspace_site_id=site-1&view=latest');
  assert.equal(seen.homeRenders, 1);
  assert.equal(context.context.workspaces[0].sites[0].hostname, 'gurbana.cl');
  assert.deepEqual(seen.requests.map(x => x.path), ['/api/privacy/diagnostic-claims', '/api/access/context']);
  assert.deepEqual(seen.requests[0].body, { diagnostic_id: 'diag-1', claim_token: 'proof', workspace_id: 'workspace-1' });
});

test('activate intent still continues to commercial handoff without showing free-save confirmation', async () => {
  const { context, seen } = freeClaimHarness('activate');
  await context.runClaim();

  assert.deepEqual(seen.redirects, ['/privacy/?workspace_site_id=site-1&view=latest&activation=pending']);
  assert.equal(context.claimSuccessPanel.hidden, true);
  assert.deepEqual(seen.requests.map(x => x.path), ['/api/privacy/diagnostic-claims']);
});

test('successful free claim remains successful when refreshing Mis sitios fails', async () => {
  const { context, seen, values } = freeClaimHarness('save', { refreshFails: true });
  await context.runClaim();

  assert.equal(context.claimSuccessPanel.hidden, false);
  assert.equal(context.pendingClaimError.hidden, true);
  assert.equal(values.size, 0);
  assert.match(context.claimSuccessDescription.textContent, /se guardó/);
  assert.deepEqual(seen.redirects, []);
});

test('failed free claim preserves pending proof and offers retry without claiming success', async () => {
  const { context, values, seen } = freeClaimHarness('save', { claimFails: true });
  await context.runClaim();

  assert.equal(values.has('mininode.privacy.pending_claim.v1'), true);
  assert.equal(context.claimSuccessPanel.hidden, true);
  assert.equal(context.pendingClaimError.hidden, false);
  assert.equal(context.pendingClaimButton.textContent, 'Reintentar guardado');
  assert.deepEqual(seen.redirects, []);
});

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

test('site rows keep result and unlink actions aligned on desktop and reflow on mobile', () => {
  const header = `blob ${Buffer.byteLength(styles, 'utf8')}\0`;
  const stylesheetSha = createHash('sha1').update(header).update(styles).digest('hex').slice(0, 12);
  assert.ok(html.includes(`./styles.css?v=${stylesheetSha}`), 'Access HTML must refresh cached CSS');
  assert.match(styles, /\.site-row \{ display: grid; grid-template-columns: minmax\(0, 1fr\) 132px 94px;/);
  assert.match(styles, /\.site-row__actions \{ grid-column: 2;/);
  assert.match(styles, /\.site-row__actions \.site-review-link \{ grid-column: auto;/);
  assert.match(styles, /\.site-unlink \{ grid-column: 3; justify-self: end;/);
  const mobile = styles.slice(styles.indexOf('@media (max-width: 640px)'));
  assert.match(mobile, /\.site-row \{ grid-template-columns: minmax\(0, 1fr\) auto;/);
  assert.match(mobile, /\.site-row__main \{ grid-column: 1 \/ -1; \}/);
  assert.match(mobile, /\.site-row__actions \{ grid-column: 1; \}/);
  assert.match(mobile, /\.site-unlink \{ grid-column: 2; \}/);
  assert.match(app, /actions\.append\(resultLink\)/);
  assert.match(app, /row\.append\(main, actions\)/);
  assert.match(app, /row\.append\(unlink\)/);
});

test('account shows the latest Privacy Web review for each site', () => {
  assert.match(app, /\/api\/privacy\/workspaces\/\$\{encodeURIComponent\(workspace\.id\)\}\/latest-reviews/);
  assert.match(app, /Última revisión: \$\{formattedDate\}/);
  assert.match(app, /pieces\.push\(\`\$\{review\.score\}\/100\`\)/);
  assert.match(app, /view=latest/);
  assert.match(app, /Ver resultado →/);
  assert.match(app, /site-review-meta/);
});

test('direct Privacy Web link requires active entitlement and preserves result', () => {
  assert.match(app, /\/api\/billing\/sites\/\$\{encodeURIComponent\(site\.id\)\}\/entitlement/);
  assert.match(app, /entitlement\?\.active !== true/);
  assert.match(app, /site-plan-link/);
  assert.match(app, /const actionsBySite = new Map\(\)/);
  assert.match(app, /actionsBySite\.set\(site\.id, actions\)/);
  assert.match(app, /actionsBySite\.get\(site\.id\)/);
  assert.match(app, /\/privacy\/plan\/\?workspace_site_id=/);
  assert.match(app, /Abrir Privacy Web →/);
  assert.match(app, /Ver resultado →/);
  assert.match(app, /requestId !== latestReviewsRequestId \|\| activeWorkspaceId !== workspace\.id/);
  assert.match(styles, /\.site-plan-link \{/);
});

test('unlink UI confirms before protected POST and preserves distinct success vs refresh errors', () => {
  assert.match(app, /window\.confirm\(/);
  assert.match(app, /\/sites\/\$\{encodeURIComponent\(site\.id\)\}\/unlink/);
  assert.match(app, /method: 'POST'/);
  assert.match(app, /\/api\/access\/context/);
  assert.match(app, /response\.status === 204/);
  assert.match(app, /El sitio fue desvinculado, pero no pudimos actualizar la lista/);
  assert.match(app, /No pudimos renovar tu sesión/);
  assert.match(app, /No pudimos conectar con Mininode/);
  assert.match(app, /site\.hostname/);
});


test('site grouping request is explicit, pending and does not merge existing account cards', () => {
  assert.match(html, /id="site-review-request"/);
  assert.match(html, /id="site-review-notice"/);
  assert.match(app, /selectedSiteReviewIds\.size !== 2/);
  assert.match(app, /siteReviewButton\.addEventListener\('click'/);
  assert.match(app, /site-group-reviews/);
  assert.match(app, /Agrupación pendiente de validación/);
  assert.match(app, /Por ahora siguen independientes/);
  assert.doesNotMatch(app, /site-group-reviews.*entitlements/);
});


function groupingHarness({ response = { status: 'pending' }, reject = false, deferred = false } = {}) {
  const makeElement = (tag = 'div') => ({
    tag, hidden: false, disabled: false, checked: false, textContent: '',
    children: [], listeners: new Map(),
    append(...items) { this.children.push(...items); },
    replaceChildren(...items) { this.children = [...items]; },
    setAttribute(name, value) { (this.attributes ||= {})[name] = value; },
    addEventListener(type, fn) { this.listeners.set(type, fn); },
  });
  const siteList = makeElement();
  const siteReviewButton = makeElement('button');
  const siteReviewNotice = makeElement('p');
  const workspacePicker = makeElement('select');
  const siteEmpty = makeElement();
  const seen = { requests: [], loads: [], renders: 0 };
  let resolveRequest;
  const promise = new Promise((resolve) => { resolveRequest = resolve; });
  const api = (path, options) => {
    seen.requests.push({ path, method: options.method, body: JSON.parse(options.body) });
    if (reject) return Promise.reject(new Error('La revisión de sitios no está disponible.'));
    return deferred ? promise : Promise.resolve(response);
  };
  const workspaceOne = {
    id: 'w1',
    sites: [
      { id: 's1', hostname: 'example.cl' },
      { id: 's2', hostname: 'www.example.cl' },
      { id: 's3', hostname: 'other.example' },
    ],
  };
  const workspaceTwo = {
    id: 'w2', sites: [{ id: 's4', hostname: 'outside.example' }],
  };
  const sandbox = {
    siteList, siteReviewButton, siteReviewNotice, workspacePicker, siteEmpty,
    document: { createElement: makeElement },
    window: { confirm: () => true, alert: () => {} },
    api, context: { workspaces: [workspaceOne, workspaceTwo] },
    activeWorkspaceId: 'w1',
    sessionStorage: { getItem: () => null },
    PENDING_CLAIM_KEY: 'none',
    renderHome() { seen.renders++; },
    loadLatestReviews(workspace) { seen.loads.push(workspace.id); },
    formatReviewDate() { return ''; },
    setVisible(element, visible) { element.hidden = !visible; },
    encodeURIComponent, console, Set, Map, Array, Error,
  };
  const renderBegin = app.indexOf('function updateSiteReviewButton(');
  const renderEnd = app.indexOf('async function loadLatestReviews(', renderBegin);
  const eventBegin = app.indexOf("siteReviewButton.addEventListener('click'");
  const eventEnd = app.indexOf("errorSignOutButton.addEventListener('click'", eventBegin);
  assert.ok(renderBegin >= 0 && renderEnd > renderBegin && eventBegin >= 0 && eventEnd > eventBegin);
  const code = [
    'let selectedSiteReviewIds = new Set();',
    app.slice(renderBegin, renderEnd),
    app.slice(eventBegin, eventEnd),
    'globalThis.render = renderSites;',
    'globalThis.selectionCount = () => selectedSiteReviewIds.size;',
  ].join('\n');
  vm.runInNewContext(code, sandbox);
  const checkbox = (row) => row.children[0].children.find((node) => node.tag === 'input');
  return {
    sandbox, seen, workspaceOne, workspaceTwo, siteList, siteReviewButton,
    siteReviewNotice, workspacePicker, checkbox, resolveRequest,
    select(rowIndex, checked) {
      const node = checkbox(siteList.children[rowIndex]);
      assert.ok(node, 'row must offer a selection checkbox');
      node.checked = checked;
      node.listeners.get('change')();
    },
  };
}

test('grouping action requires exactly two site selections and preserves all cards', () => {
  const h = groupingHarness();
  h.sandbox.render(h.workspaceOne, []);
  assert.equal(h.siteList.children.length, 3);
  assert.equal(h.siteReviewButton.disabled, true);
  h.select(0, true);
  assert.equal(h.siteReviewButton.disabled, true);
  h.select(1, true);
  assert.equal(h.siteReviewButton.disabled, false);
  h.select(2, true);
  assert.equal(h.siteReviewButton.disabled, true);
  h.select(2, false);
  assert.equal(h.siteReviewButton.disabled, false);
  h.select(0, false);
  assert.equal(h.siteReviewButton.disabled, true);
});

test('successful and repeated pending requests show status without merging cards', async () => {
  const h = groupingHarness();
  h.sandbox.render(h.workspaceOne);
  h.select(0, true); h.select(1, true);
  await h.siteReviewButton.listeners.get('click')();
  assert.equal(h.seen.requests.length, 1);
  assert.equal(h.seen.requests[0].path, '/api/access/workspaces/w1/site-group-reviews');
  assert.deepEqual(h.seen.requests[0].body,
    { first_workspace_site_id: 's1', second_workspace_site_id: 's2' });
  assert.match(h.siteReviewNotice.textContent, /Solicitud recibida/);
  assert.equal(h.siteList.children.length, 3);

  h.sandbox.render(h.workspaceOne, [], [{
    first_workspace_site_id: 's1', second_workspace_site_id: 's2', status: 'pending',
  }]);
  const labels = h.siteList.children[0].children[0].children.map((el) => el.textContent);
  assert.ok(labels.includes('Agrupación pendiente de validación'));
  h.select(0, true); h.select(1, true);
  await h.siteReviewButton.listeners.get('click')();
  assert.equal(h.seen.requests.length, 2);
  assert.match(h.siteReviewNotice.textContent, /Solicitud recibida/);
  assert.equal(h.siteList.children.length, 3);
});

test('503 before migration leaves user selection available to retry', async () => {
  const h = groupingHarness({ reject: true });
  h.sandbox.render(h.workspaceOne);
  h.select(0, true); h.select(1, true);
  await h.siteReviewButton.listeners.get('click')();
  assert.match(h.siteReviewNotice.textContent, /no está disponible/);
  assert.equal(h.siteReviewButton.disabled, false);
  assert.equal(h.sandbox.selectionCount(), 2);
});

test('workspace switch during review submission discards stale success', async () => {
  const h = groupingHarness({ deferred: true });
  h.sandbox.render(h.workspaceOne);
  h.select(0, true); h.select(1, true);
  const pending = h.siteReviewButton.listeners.get('click')();
  assert.equal(h.seen.requests.length, 1);
  h.workspacePicker.value = 'w2';
  h.workspacePicker.listeners.get('change')();
  assert.equal(h.sandbox.activeWorkspaceId, 'w2');
  assert.equal(h.sandbox.selectionCount(), 0);
  assert.equal(h.siteReviewNotice.textContent, '');
  assert.equal(h.seen.renders, 1);
  h.resolveRequest({ status: 'pending' });
  await pending;
  assert.deepEqual(h.seen.loads, []);
  assert.equal(h.siteReviewNotice.textContent, '');
});
