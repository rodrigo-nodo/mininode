const ACCESS_PATH = '/access/';

function mininodeTheme() {
  const explicit = document.documentElement.dataset.theme;
  if (explicit === 'light' || explicit === 'dark') return explicit;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function signInAppearance() {
  const dark = mininodeTheme() === 'dark';
  return {
    theme: 'simple',
    variables: {
      colorPrimary: dark ? '#66c6d0' : '#176b78',
      colorForeground: dark ? '#f4f2fa' : '#0d0f14',
      colorMutedForeground: dark ? '#b5b1be' : '#626570',
      colorBackground: dark ? '#111218' : '#ffffff',
      colorInput: dark ? '#111218' : '#ffffff',
      colorInputForeground: dark ? '#f4f2fa' : '#0d0f14',
      colorBorder: dark ? '#3a3d47' : '#d9dde5',
      borderRadius: '10px',
      fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif',
    },
    options: {
      elevation: 'flush',
      socialButtonsPlacement: 'top',
      socialButtonsVariant: 'blockButton',
      privacyPageUrl: '/legal/privacy/',
    },
    elements: {
      rootBox: { width: '100%' },
      cardBox: { width: '100%', maxWidth: '100%', boxShadow: 'none', overflow: 'visible' },
      card: { width: '100%', boxShadow: 'none', border: '0', padding: '0', background: 'transparent' },
      header: { display: 'none' },
      footer: { display: 'none' },
      lastAuthenticationStrategyBadge: { display: 'none' },
      socialButtonsBlockButton: {
        minHeight: '46px',
        color: dark ? '#f4f2fa' : '#0d0f14',
        backgroundColor: dark ? '#111218' : '#ffffff',
        borderColor: dark ? '#3a3d47' : '#d9dde5',
      },
      formFieldInput: { minHeight: '46px' },
      formButtonPrimary: { minHeight: '46px', textTransform: 'none', fontWeight: '650' },
    },
  };
}

const localization = {
  locale: 'es-ES', backButton: 'Volver', dividerText: 'o', formButtonPrimary: 'Continuar',
  formButtonPrimary__verify: 'Verificar', formFieldLabel__emailAddress: 'Correo electrónico',
  formFieldInputPlaceholder__emailAddress: 'nombre@empresa.cl', footerActionLink__useAnotherMethod: 'Usar otro método',
  socialButtonsBlockButton: 'Continuar con {{provider|titleize}}', socialButtonsBlockButtonManyInView: '{{provider|titleize}}',
  signIn: { start: { actionLink: 'Crear cuenta', actionText: '¿No tienes cuenta?', subtitle: 'para continuar a Mininode', subtitleCombined: 'para continuar a Mininode', title: 'Acceder', titleCombined: 'Continuar a Mininode' },
    emailCode: { formTitle: 'Código de acceso', resendButton: 'Reenviar código', subtitle: 'para continuar a Mininode', title: 'Revisa tu correo' } },
  signUp: { start: { actionLink: 'Acceder', actionText: '¿Ya tienes una cuenta?', subtitle: 'para continuar a Mininode', subtitleCombined: 'para continuar a Mininode', title: 'Crear cuenta', titleCombined: 'Continuar a Mininode' },
    emailCode: { formSubtitle: 'Ingresa el código enviado a tu correo electrónico.', formTitle: 'Código de acceso', resendButton: 'Reenviar código', subtitle: 'para continuar a Mininode', title: 'Verifica tu correo' } },
};

const loginPanel = document.querySelector('#access-login');
const loading = document.querySelector('#access-loading');
const signInNode = document.querySelector('#clerk-sign-in');
const errorPanel = document.querySelector('#access-error');
const errorMessage = document.querySelector('#access-error-message');
const note = document.querySelector('#access-note');
const home = document.querySelector('#account-home');
const retryButton = document.querySelector('#access-retry');
const errorSignOutButton = document.querySelector('#access-error-sign-out');
const workspacePickerLabel = document.querySelector('#workspace-picker-label');
const workspacePicker = document.querySelector('#workspace-picker');
const privacyWebOpen = document.querySelector('#privacy-web-open');
const siteList = document.querySelector('#site-list');
const siteReviewButton = document.querySelector('#site-review-request');
const siteReviewNotice = document.querySelector('#site-review-notice');
const pendingClaimPanel = document.querySelector('#pending-claim-panel');
const pendingClaimButton = document.querySelector('#pending-claim-button');
const pendingClaimError = document.querySelector('#pending-claim-error');
const claimSuccessPanel = document.querySelector('#claim-success');
const claimSuccessDescription = document.querySelector('#claim-success-description');
const claimSuccessResult = document.querySelector('#claim-success-result');
const PENDING_CLAIM_KEY = 'mininode.privacy.pending_claim.v1';
const siteEmpty = document.querySelector('#site-empty');

let signInMounted = false;
let lastResolvedSessionId = null;
let syncInFlight = false;
let syncRequested = false;
let context = { workspaces: [] };
let activeWorkspaceId = '';
let latestReviewsRequestId = 0;
let claimInFlight = false;
let pendingWorkspaceChoice = false;
let selectedSiteReviewIds = new Set();

let mininodeAuth = null;

function waitForMininodeAuth() {
  if (window.MininodeAuth) return Promise.resolve(window.MininodeAuth);
  return new Promise((resolve) => {
    window.addEventListener('mininode:auth-api-ready', () => resolve(window.MininodeAuth), { once: true });
  });
}

function setVisible(element, visible) {
  if (!element) return;
  element.hidden = !visible;
}

function showLoading(message = 'Preparando acceso…') {
  loading.textContent = message;
  setVisible(loginPanel, true); setVisible(loading, true); setVisible(signInNode, false);
  setVisible(errorPanel, false); setVisible(home, false);
}

function showSignedOut() {
  lastResolvedSessionId = null; context = { workspaces: [] }; activeWorkspaceId = '';
  claimSuccessPanel.hidden = true;
  setVisible(loginPanel, true); setVisible(loading, false); setVisible(errorPanel, false);
  setVisible(home, false); setVisible(signInNode, true); setVisible(note, true);
  if (!signInMounted) {
    mininodeAuth.mountSignIn(signInNode, { routing: 'hash', withSignUp: true, appearance: signInAppearance(), signInForceRedirectUrl: ACCESS_PATH, signUpForceRedirectUrl: ACCESS_PATH });
    signInMounted = true;
  }
}

function unmountSignIn() {
  if (!signInMounted) return;
  mininodeAuth?.unmountSignIn(signInNode); signInMounted = false;
}

function showError(message) {
  unmountSignIn(); setVisible(loginPanel, true); setVisible(loading, false); setVisible(signInNode, false);
  const hasSession = Boolean(mininodeAuth?.isSignedIn());
  setVisible(home, false); setVisible(errorPanel, true); setVisible(note, true);
  setVisible(errorSignOutButton, hasSession);
  errorMessage.textContent = message;
}

async function api(path, options = {}) {
  let token;
  try {
    token = await mininodeAuth.getToken();
  } catch {
    throw new Error('No pudimos renovar tu sesión. Recarga la página y vuelve a intentarlo.');
  }
  if (!token) throw new Error('Tu sesión ya no está disponible. Vuelve a acceder.');

  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), Authorization: `Bearer ${token}`, ...(options.headers || {}) },
    });
  } catch {
    throw new Error('No pudimos conectar con Mininode. Revisa tu conexión e inténtalo nuevamente.');
  }
  if (!response.ok) {
    if (response.status === 401) throw new Error('Tu sesión ya no puede validarse. Cierra la sesión y vuelve a acceder.');
    if (response.status === 503) throw new Error('El servicio de acceso está temporalmente no disponible.');
    if (path === '/api/privacy/diagnostic-claims' && response.status === 422) {
      throw new Error('No pudimos validar los datos del diagnóstico. Puedes reintentarlo o realizar una nueva revisión.');
    }
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : 'No pudimos completar la solicitud.');
  }
  if (response.status === 204) return null;
  return response.json();
}

async function loadAccount(session) {
  if (!session) throw new Error('El servicio de acceso no entregó una sesión válida.');

  await api('/api/access/me');
  let nextContext = await api('/api/access/context');
  if (!Array.isArray(nextContext.workspaces) || nextContext.workspaces.length === 0) {
    await api('/api/access/onboarding', { method: 'POST' });
    nextContext = await api('/api/access/context');
  }
  context = nextContext;
  activeWorkspaceId = context.workspaces[0]?.id || '';
  renderHome();
}

function formatReviewDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('es-CL', {
    timeZone: 'America/Santiago',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

function updateSiteReviewButton(siteCount) {
  siteReviewButton.hidden = siteCount < 2;
  siteReviewButton.disabled = selectedSiteReviewIds.size !== 2;
}

function renderSites(workspace, reviews = [], groupReviews = []) {
  siteList.replaceChildren();
  const sites = Array.isArray(workspace?.sites) ? workspace.sites : [];
  const reviewsBySite = new Map(
    (Array.isArray(reviews) ? reviews : [])
      .filter((review) => review?.workspace_site_id)
      .map((review) => [review.workspace_site_id, review]),
  );

  const reviewItems = Array.isArray(groupReviews) ? groupReviews : [];
  const pendingSiteIds = new Set(reviewItems
    .filter((item) => item.status === 'pending')
    .flatMap((item) => [item.first_workspace_site_id, item.second_workspace_site_id]));
  const approvedSiteIds = new Set(reviewItems
    .filter((item) => item.status === 'approved')
    .flatMap((item) => [item.first_workspace_site_id, item.second_workspace_site_id]));
  const rejectedSiteIds = new Set(reviewItems
    .filter((item) => item.status === 'rejected')
    .flatMap((item) => [item.first_workspace_site_id, item.second_workspace_site_id]));
  selectedSiteReviewIds = new Set([...selectedSiteReviewIds].filter((id) => sites.some((site) => site.id === id)));

  sites.forEach((site) => {
    const row = document.createElement('div');
    row.dataset.workspaceSiteId = site.id;
    const actions = document.createElement('div');
    actions.className = 'site-row__actions';
    row.className = 'site-row';

    const main = document.createElement('div');
    main.className = 'site-row__main';

    const link = document.createElement('a');
    link.className = 'site-link';
    link.href = `/privacy/?workspace_site_id=${encodeURIComponent(site.id)}`;
    link.textContent = site.hostname;
    link.setAttribute('aria-label', `Abrir Privacy Web para ${site.hostname}`);
    if (sites.length > 1) {
      const select = document.createElement('input');
      select.type = 'checkbox';
      select.className = 'site-group-checkbox';
      select.checked = selectedSiteReviewIds.has(site.id);
      select.setAttribute('aria-label', `Seleccionar ${site.hostname} para revisión de agrupación`);
      select.addEventListener('change', () => {
        if (select.checked) selectedSiteReviewIds.add(site.id);
        else selectedSiteReviewIds.delete(site.id);
        updateSiteReviewButton(sites.length);
      });
      main.append(select);
    }
    main.append(link);

    if (pendingSiteIds.has(site.id) || approvedSiteIds.has(site.id) || rejectedSiteIds.has(site.id)) {
      const state = document.createElement('p');
      state.className = 'site-review-meta';
      state.textContent = pendingSiteIds.has(site.id) ? 'Agrupación pendiente de validación'
        : approvedSiteIds.has(site.id) ? 'Agrupación aprobada' : 'Agrupación rechazada';
      main.append(state);
    }

    const review = reviewsBySite.get(site.id);
    if (review && Number.isFinite(review.score)) {
      const meta = document.createElement('p');
      meta.className = 'site-review-meta';
      const formattedDate = formatReviewDate(review.created_at);
      const pieces = [formattedDate ? `Última revisión: ${formattedDate}` : 'Última revisión'];
      pieces.push(`${review.score}/100`);
      if (typeof review.status === 'string' && review.status.trim()) pieces.push(review.status.trim());
      meta.textContent = pieces.join(' · ');
      main.append(meta);

      const resultLink = document.createElement('a');
      resultLink.className = 'site-review-link';
      resultLink.href = `/privacy/?workspace_site_id=${encodeURIComponent(site.id)}&view=latest`;
      resultLink.textContent = 'Ver resultado →';
      resultLink.setAttribute('aria-label', `Ver última revisión de ${site.hostname}`);
      actions.append(resultLink);
      row.append(main, actions);
    } else {
      row.append(main, actions);
    }

    const unlink = document.createElement('button');
    unlink.type = 'button';
    unlink.className = 'site-unlink';
    unlink.textContent = 'Desvincular';
    unlink.setAttribute('aria-label', `Desvincular ${site.hostname}`);
    unlink.addEventListener('click', async () => {
      if (!window.confirm(`¿Desvincular ${site.hostname} de este espacio? Los diagnósticos se conservan.`)) return;
      unlink.disabled = true;
      try {
        await api(`/api/access/workspaces/${encodeURIComponent(workspace.id)}/sites/${encodeURIComponent(site.id)}/unlink`, { method: 'POST' });
      } catch (error) {
        unlink.disabled = false;
        window.alert(error instanceof Error ? error.message : 'No pudimos desvincular el sitio.');
        return;
      }
      try {
        context = await api('/api/access/context');
        renderHome();
      } catch {
        unlink.disabled = false;
        window.alert('El sitio fue desvinculado, pero no pudimos actualizar la lista. Recarga la página.');
      }
    });
    row.append(unlink);
    siteList.append(row);
  });
  setVisible(siteEmpty, sites.length === 0);
  updateSiteReviewButton(sites.length);
}

async function loadEntitledPlanLinks(workspace, requestId) {
  const sites = Array.isArray(workspace?.sites) ? workspace.sites : [];
  await Promise.all(sites.map(async (site) => {
    try {
      const entitlement = await api(`/api/billing/sites/${encodeURIComponent(site.id)}/entitlement`);
      if (requestId !== latestReviewsRequestId || activeWorkspaceId !== workspace.id) return;
      if (entitlement?.active !== true) return;
      const row = [...siteList.querySelectorAll('.site-row')]
        .find((item) => item.dataset.workspaceSiteId === site.id);
      const actions = row?.querySelector('.site-row__actions');
      if (!actions || actions.querySelector('.site-plan-link')) return;
      const link = document.createElement('a');
      link.className = 'site-plan-link';
      link.href = `/privacy/plan/?workspace_site_id=${encodeURIComponent(site.id)}`;
      link.textContent = 'Abrir Privacy Web →';
      link.setAttribute('aria-label', `Abrir Privacy Web para ${site.hostname}`);
      actions.append(link);
    } catch {
      // A transient entitlement error must not be interpreted as an active grant.
      // The existing saved diagnostic and its result link remain available.
    }
  }));
}

async function loadLatestReviews(workspace) {
  const requestId = ++latestReviewsRequestId;
  const [latest, grouping] = await Promise.allSettled([
    api(`/api/privacy/workspaces/${encodeURIComponent(workspace.id)}/latest-reviews`),
    api(`/api/access/workspaces/${encodeURIComponent(workspace.id)}/site-group-reviews`),
  ]);
  if (requestId !== latestReviewsRequestId || activeWorkspaceId !== workspace.id) return;
  renderSites(
    workspace,
    latest.status === 'fulfilled' && Array.isArray(latest.value.reviews) ? latest.value.reviews : [],
    grouping.status === 'fulfilled' && Array.isArray(grouping.value.reviews) ? grouping.value.reviews : [],
  );
  void loadEntitledPlanLinks(workspace, requestId);
}

function renderHome() {
  const workspaces = Array.isArray(context.workspaces) ? context.workspaces : [];
  const active = workspaces.find((workspace) => workspace.id === activeWorkspaceId) || workspaces[0];
  if (!active) throw new Error('No pudimos preparar tu espacio Mininode.');
  activeWorkspaceId = active.id;

  workspacePicker.replaceChildren();
  workspaces.forEach((workspace) => {
    const option = document.createElement('option');
    option.value = workspace.id; option.textContent = workspace.name;
    workspacePicker.append(option);
  });
  workspacePicker.value = active.id;
  if (sessionStorage.getItem(PENDING_CLAIM_KEY) && workspaces.length > 1) {
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Selecciona un espacio para guardar';
    placeholder.disabled = true;
    workspacePicker.prepend(placeholder);
    workspacePicker.value = '';
  }
  setVisible(workspacePickerLabel, workspaces.length > 1);
  privacyWebOpen.href = `/privacy/?workspace_id=${encodeURIComponent(active.id)}`;
  const pending = sessionStorage.getItem(PENDING_CLAIM_KEY);
  let isActivation = false;
  try { isActivation = JSON.parse(pending || 'null')?.intent === 'activate'; } catch { /* handled on save attempt */ }
  pendingClaimPanel.hidden = !pending;
  pendingClaimButton.hidden = true;
  pendingWorkspaceChoice = Boolean(pending && workspaces.length > 1);
  const claimTitle = pendingClaimPanel.querySelector('h2');
  const claimDescription = pendingClaimPanel.querySelector('p');
  if (claimTitle) claimTitle.textContent = pendingWorkspaceChoice ? 'Elige dónde guardar el diagnóstico' : 'Guardando tu diagnóstico…';
  if (claimDescription) claimDescription.textContent = pendingWorkspaceChoice
    ? 'Selecciona un espacio para continuar. Guardaremos el diagnóstico automáticamente.'
    : isActivation ? 'Conservaremos el diagnóstico y continuaremos con Privacy Web.' : 'Conservaremos el resultado en tu espacio.';
  pendingClaimError.hidden = true;
  renderSites(active);

  unmountSignIn(); setVisible(loginPanel, false); setVisible(home, true);
  void loadLatestReviews(active);
  if (pending && !pendingWorkspaceChoice) void savePendingDiagnostic();
}

async function syncAuthState(session) {
  if (!session) { showSignedOut(); return; }
  if (lastResolvedSessionId === session.id && !home.hidden) return;
  showLoading('Preparando tu espacio…');
  try {
    await loadAccount(session);
    lastResolvedSessionId = session.id;
  } catch (error) {
    showError(error instanceof Error ? error.message : 'No pudimos completar el acceso.');
  }
}

async function requestSync(session) {
  if (syncInFlight) { syncRequested = true; return; }
  syncInFlight = true;
  try { await syncAuthState(session); }
  finally {
    syncInFlight = false;
    if (syncRequested) { syncRequested = false; await requestSync(mininodeAuth.session()); }
  }
}

async function signOut() {
  showLoading('Cerrando sesión…');
  try { await mininodeAuth.signOut(); } catch { showError('No pudimos cerrar la sesión. Intenta nuevamente.'); }
}

function showSavedDiagnosticConfirmation(workspaceSiteId, hostname = '') {
  pendingClaimPanel.hidden = true;
  claimSuccessPanel.hidden = false;
  claimSuccessDescription.textContent = hostname
    ? `El diagnóstico de ${hostname} está disponible en Mis sitios.`
    : 'Tu diagnóstico está disponible en Mi espacio, dentro de Mis sitios.';
  claimSuccessResult.href = `/privacy/?workspace_site_id=${encodeURIComponent(workspaceSiteId)}&view=latest`;
}

async function savePendingDiagnostic() {
  if (claimInFlight) return;
  claimInFlight = true;
  const raw = sessionStorage.getItem(PENDING_CLAIM_KEY);
  if (!raw) { pendingClaimPanel.hidden = true; claimInFlight = false; return; }
  let claim;
  try { claim = JSON.parse(raw); } catch { sessionStorage.removeItem(PENDING_CLAIM_KEY); pendingClaimPanel.hidden = true; claimInFlight = false; return; }
  if (typeof claim?.diagnostic_id !== 'string' || typeof claim?.claim_token !== 'string') {
    sessionStorage.removeItem(PENDING_CLAIM_KEY); pendingClaimPanel.hidden = true; claimInFlight = false; return;
  }
  pendingClaimPanel.hidden = false;
  pendingClaimButton.hidden = true;
  pendingClaimError.hidden = true;
  workspacePicker.disabled = true;
  const claimTitle = pendingClaimPanel.querySelector('h2');
  if (claimTitle) claimTitle.textContent = 'Guardando tu diagnóstico…';
  try {
    // The API accepts exactly three fields; intent stays client-side for navigation.
    const saved = await api('/api/privacy/diagnostic-claims', {
      method: 'POST',
      body: JSON.stringify({
        diagnostic_id: claim.diagnostic_id,
        claim_token: claim.claim_token,
        workspace_id: activeWorkspaceId,
      }),
    });
    sessionStorage.removeItem(PENDING_CLAIM_KEY);
    if (claim.intent === 'activate') {
      window.location.assign('/privacy/?workspace_site_id='
        + encodeURIComponent(saved.workspace_site_id) + '&view=latest&activation=pending');
      return;
    }

    // Free save ends in Mi espacio, not back in the diagnostic.
    showSavedDiagnosticConfirmation(saved.workspace_site_id);
    try {
      const updatedContext = await api('/api/access/context');
      const savedWorkspace = (Array.isArray(updatedContext.workspaces) ? updatedContext.workspaces : [])
        .find((workspace) => workspace.id === activeWorkspaceId);
      if (!savedWorkspace) throw new Error('Saved workspace unavailable in account refresh');
      context = updatedContext;
      renderHome();
      const site = (Array.isArray(savedWorkspace.sites) ? savedWorkspace.sites : [])
        .find((item) => item.id === saved.workspace_site_id);
      showSavedDiagnosticConfirmation(saved.workspace_site_id, site?.hostname || '');
    } catch {
      // The claim is already committed. Never report a refresh failure as a failed save.
      claimSuccessDescription.textContent = 'El diagnóstico se guardó. Si aún no aparece en Mis sitios, recarga la cuenta o selecciona Ver resultado.';
    }
  } catch (error) {
    pendingClaimError.textContent = error instanceof Error ? error.message : 'No pudimos guardar el diagnóstico. Reintenta el guardado.';
    pendingClaimError.hidden = false;
    pendingClaimButton.hidden = false;
    pendingClaimButton.textContent = 'Reintentar guardado';
    if (claimTitle) claimTitle.textContent = 'No pudimos guardar el diagnóstico';
  } finally {
    workspacePicker.disabled = false;
    claimInFlight = false;
  }
}
pendingClaimButton.addEventListener('click', () => { void savePendingDiagnostic(); });

siteReviewButton.addEventListener('click', async () => {
  if (selectedSiteReviewIds.size !== 2 || !activeWorkspaceId) return;
  const workspaceId = activeWorkspaceId;
  const [first, second] = [...selectedSiteReviewIds];
  siteReviewButton.disabled = true;
  siteReviewNotice.textContent = 'Enviando solicitud…';
  try {
    const result = await api(`/api/access/workspaces/${encodeURIComponent(workspaceId)}/site-group-reviews`, {
      method: 'POST',
      body: JSON.stringify({
        first_workspace_site_id: first,
        second_workspace_site_id: second,
      }),
    });
    if (activeWorkspaceId !== workspaceId) return;
    siteReviewNotice.textContent = result.status === 'pending'
      ? 'Solicitud recibida. Validaremos si estos sitios pueden agruparse. Por ahora siguen independientes.'
      : 'Esta solicitud ya fue revisada. Los sitios siguen independientes.';
    selectedSiteReviewIds.clear();
    const workspace = context.workspaces.find((item) => item.id === workspaceId);
    if (workspace) void loadLatestReviews(workspace);
  } catch (error) {
    if (activeWorkspaceId === workspaceId) {
      siteReviewNotice.textContent = error instanceof Error ? error.message : 'No pudimos enviar la solicitud.';
      const workspace = context.workspaces.find((item) => item.id === workspaceId);
      updateSiteReviewButton(Array.isArray(workspace?.sites) ? workspace.sites.length : 0);
    }
  }
});

workspacePicker.addEventListener('change', () => {
  if (!workspacePicker.value) return;
  activeWorkspaceId = workspacePicker.value;
  selectedSiteReviewIds.clear();
  siteReviewNotice.textContent = '';
  if (sessionStorage.getItem(PENDING_CLAIM_KEY)) {
    pendingWorkspaceChoice = false;
    void savePendingDiagnostic();
    return;
  }
  renderHome();
});
errorSignOutButton.addEventListener('click', signOut);
retryButton.addEventListener('click', () => {
  lastResolvedSessionId = null;
  void requestSync(mininodeAuth?.session() || null);
});

window.addEventListener('load', async () => {
  try {
    showLoading('Leyendo configuración de acceso…');
    mininodeAuth = await waitForMininodeAuth();
    await mininodeAuth.ready({ ui: true, localization });
    mininodeAuth.subscribe(({ session }) => { void requestSync(session); }, { emitCurrent: false });
    await requestSync(mininodeAuth.session());
  } catch {
    showError('No pudimos iniciar el servicio de acceso. Intenta nuevamente.');
  }
});
