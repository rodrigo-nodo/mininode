const ACCESS_PATH = '/access/';

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
const signOutButton = document.querySelector('#access-sign-out');
const retryButton = document.querySelector('#access-retry');
const errorSignOutButton = document.querySelector('#access-error-sign-out');
const workspacePickerLabel = document.querySelector('#workspace-picker-label');
const workspacePicker = document.querySelector('#workspace-picker');
const siteList = document.querySelector('#site-list');
const siteEmpty = document.querySelector('#site-empty');
const siteAddOpen = document.querySelector('#site-add-open');
const siteAddForm = document.querySelector('#site-add-form');
const siteUrl = document.querySelector('#site-url');
const siteAddError = document.querySelector('#site-add-error');

let signInMounted = false;
let lastResolvedSessionId = null;
let syncInFlight = false;
let syncRequested = false;
let context = { workspaces: [] };
let activeWorkspaceId = '';

function setVisible(element, visible) {
  if (!element) return;
  element.hidden = !visible;
}

function showLoading(message = 'Preparando acceso…') {
  loading.textContent = message;
  setVisible(loginPanel, true); setVisible(loading, true); setVisible(signInNode, false);
  setVisible(errorPanel, false); setVisible(home, false); setVisible(signOutButton, false);
}

function showSignedOut() {
  lastResolvedSessionId = null; context = { workspaces: [] }; activeWorkspaceId = '';
  setVisible(loginPanel, true); setVisible(loading, false); setVisible(errorPanel, false);
  setVisible(home, false); setVisible(signOutButton, false); setVisible(signInNode, true); setVisible(note, true);
  if (!signInMounted) {
    Clerk.mountSignIn(signInNode, { routing: 'hash', withSignUp: true, signInForceRedirectUrl: ACCESS_PATH, signUpForceRedirectUrl: ACCESS_PATH });
    signInMounted = true;
  }
}

function unmountSignIn() {
  if (!signInMounted) return;
  Clerk.unmountSignIn(signInNode); signInMounted = false;
}

function showError(message) {
  unmountSignIn(); setVisible(loginPanel, true); setVisible(loading, false); setVisible(signInNode, false);
  setVisible(home, false); setVisible(signOutButton, Boolean(Clerk.session)); setVisible(errorPanel, true); setVisible(note, true);
  setVisible(errorSignOutButton, Boolean(Clerk.session));
  errorMessage.textContent = message;
}

async function api(path, options = {}) {
  const token = await Clerk.session?.getToken();
  if (!token) throw new Error('Tu sesión ya no está disponible. Vuelve a acceder.');

  const response = await fetch(path, {
    ...options,
    headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), Authorization: `Bearer ${token}`, ...(options.headers || {}) },
  });
  if (!response.ok) {
    if (response.status === 401) throw new Error('Tu sesión ya no puede validarse. Cierra la sesión y vuelve a acceder.');
    if (response.status === 503) throw new Error('El servicio de acceso está temporalmente no disponible.');
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : 'No pudimos completar la solicitud.');
  }
  return response.json();
}

async function loadAccount(session) {
  if (!session) throw new Error('Clerk no entregó una sesión válida.');

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

function renderSites(workspace) {
  siteList.replaceChildren();
  const sites = Array.isArray(workspace?.sites) ? workspace.sites : [];
  sites.forEach((site) => {
    const row = document.createElement('div');
    row.className = 'site-row';
    const link = document.createElement('a');
    link.className = 'site-link';
    link.href = `/privacy/?workspace_site_id=${encodeURIComponent(site.id)}`;
    link.textContent = site.hostname;
    link.setAttribute('aria-label', `Abrir Privacy Web para ${site.hostname}`);
    row.append(link);
    siteList.append(row);
  });
  setVisible(siteEmpty, sites.length === 0);
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
  setVisible(workspacePickerLabel, workspaces.length > 1);
  renderSites(active);

  unmountSignIn(); setVisible(loginPanel, false); setVisible(home, true); setVisible(signOutButton, true);
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
    if (syncRequested) { syncRequested = false; await requestSync(Clerk.session); }
  }
}

async function signOut() {
  showLoading('Cerrando sesión…');
  try { await Clerk.signOut(); } catch { showError('No pudimos cerrar la sesión. Intenta nuevamente.'); }
}

workspacePicker.addEventListener('change', () => { activeWorkspaceId = workspacePicker.value; renderHome(); });
siteAddOpen.addEventListener('click', () => { setVisible(siteAddForm, true); siteAddOpen.hidden = true; siteUrl.focus(); });
siteAddForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  siteAddError.hidden = true;
  const submit = siteAddForm.querySelector('button[type="submit"]');
  submit.disabled = true;
  try {
    await api(`/api/access/workspaces/${activeWorkspaceId}/sites`, { method: 'POST', body: JSON.stringify({ url: siteUrl.value }) });
    context = await api('/api/access/context');
    siteUrl.value = ''; siteAddForm.hidden = true; siteAddOpen.hidden = false; renderHome();
  } catch (error) {
    siteAddError.textContent = error instanceof Error ? error.message : 'No pudimos agregar el sitio.';
    siteAddError.hidden = false;
  } finally { submit.disabled = false; }
});

signOutButton.addEventListener('click', signOut);
errorSignOutButton.addEventListener('click', signOut);
retryButton.addEventListener('click', () => { lastResolvedSessionId = null; void requestSync(Clerk.session); });

window.addEventListener('load', async () => {
  if (!window.Clerk || !window.__internal_ClerkUICtor) { showError('No pudimos cargar el servicio de acceso.'); return; }
  try {
    await Clerk.load({
      ui: { ClerkUI: window.__internal_ClerkUICtor }, localization,
      appearance: {
        variables: { colorPrimary: 'var(--color-primary)', colorText: 'var(--color-text)', colorTextSecondary: 'var(--color-muted)', colorBackground: 'transparent', colorInputBackground: 'var(--color-bg)', colorInputText: 'var(--color-text)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-body)' },
        options: { elevation: 'flush', socialButtonsPlacement: 'top', socialButtonsVariant: 'blockButton', privacyPageUrl: '/legal/privacy/' },
        elements: {
          rootBox: { width: '100%' }, cardBox: { width: '100%', maxWidth: '100%', boxShadow: 'none', overflow: 'visible' },
          card: { width: '100%', boxShadow: 'none', border: '0', padding: '0', background: 'transparent' },
          header: { display: 'none' }, footer: { display: 'none' }, lastAuthenticationStrategyBadge: { display: 'none' },
          socialButtonsBlockButton: { minHeight: '46px', borderColor: 'var(--color-border)', color: 'var(--color-text)' },
          formFieldInput: { minHeight: '46px', borderColor: 'var(--color-border)' },
          formButtonPrimary: { minHeight: '46px', backgroundColor: 'var(--color-primary)', textTransform: 'none', fontWeight: '650' },
        },
      },
    });
    Clerk.addListener(({ session }) => { void requestSync(session); }, { skipInitialEmit: true });
    await requestSync(Clerk.session);
  } catch { showError('No pudimos iniciar el servicio de acceso. Intenta nuevamente.'); }
});
