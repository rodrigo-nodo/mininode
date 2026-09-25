const ACCESS_PATH = '/access/';

const localization = {
  locale: 'es-ES',
  backButton: 'Volver',
  dividerText: 'o',
  formButtonPrimary: 'Continuar',
  formButtonPrimary__verify: 'Verificar',
  formFieldLabel__emailAddress: 'Correo electrónico',
  formFieldInputPlaceholder__emailAddress: 'nombre@empresa.cl',
  socialButtonsBlockButton: 'Continuar con {{provider|titleize}}',
  socialButtonsBlockButtonManyInView: '{{provider|titleize}}',
  signIn: {
    start: {
      actionLink: 'Crear cuenta',
      actionText: '¿No tienes cuenta?',
      subtitle: 'para continuar a Mininode',
      subtitleCombined: 'para continuar a Mininode',
      title: 'Acceder',
      titleCombined: 'Continuar a Mininode',
    },
    emailCode: {
      formTitle: 'Código de acceso',
      resendButton: 'Reenviar código',
      subtitle: 'para continuar a Mininode',
      title: 'Revisa tu correo',
    },
  },
  signUp: {
    start: {
      actionLink: 'Acceder',
      actionText: '¿Ya tienes una cuenta?',
      subtitle: 'para continuar a Mininode',
      subtitleCombined: 'para continuar a Mininode',
      title: 'Crear cuenta',
      titleCombined: 'Continuar a Mininode',
    },
    emailCode: {
      formSubtitle: 'Ingresa el código enviado a tu correo electrónico.',
      formTitle: 'Código de acceso',
      resendButton: 'Reenviar código',
      subtitle: 'para continuar a Mininode',
      title: 'Verifica tu correo',
    },
  },
};

const loading = document.querySelector('#access-loading');
const signInNode = document.querySelector('#clerk-sign-in');
const sessionPanel = document.querySelector('#access-session');
const emailNode = document.querySelector('#access-email');
const errorPanel = document.querySelector('#access-error');
const errorMessage = document.querySelector('#access-error-message');
const note = document.querySelector('#access-note');
const signOutButton = document.querySelector('#access-sign-out');
const retryButton = document.querySelector('#access-retry');
const errorSignOutButton = document.querySelector('#access-error-sign-out');

let signInMounted = false;
let lastResolvedSessionId = null;
let syncInFlight = false;
let syncRequested = false;

function setVisible(element, visible) {
  element.hidden = !visible;
}

function showLoading(message = 'Preparando acceso…') {
  loading.textContent = message;
  setVisible(loading, true);
  setVisible(signInNode, false);
  setVisible(sessionPanel, false);
  setVisible(errorPanel, false);
}

function showSignedOut() {
  lastResolvedSessionId = null;
  setVisible(loading, false);
  setVisible(sessionPanel, false);
  setVisible(errorPanel, false);
  setVisible(signInNode, true);
  setVisible(note, true);

  if (!signInMounted) {
    Clerk.mountSignIn(signInNode, {
      routing: 'hash',
      withSignUp: true,
      signInForceRedirectUrl: ACCESS_PATH,
      signUpForceRedirectUrl: ACCESS_PATH,
    });
    signInMounted = true;
  }
}

function unmountSignIn() {
  if (!signInMounted) return;
  Clerk.unmountSignIn(signInNode);
  signInMounted = false;
}

function showError(message) {
  unmountSignIn();
  setVisible(loading, false);
  setVisible(signInNode, false);
  setVisible(sessionPanel, false);
  setVisible(errorPanel, true);
  setVisible(note, true);
  errorMessage.textContent = message;
}

async function resolveMininodeIdentity(session) {
  const token = await session.getToken();
  if (!token) throw new Error('Clerk no entregó una sesión válida.');

  const response = await fetch('/api/access/me', {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('La sesión fue creada, pero Mininode no pudo validarla.');
    }
    if (response.status === 503) {
      throw new Error('El servicio de acceso está temporalmente no disponible.');
    }
    throw new Error('No pudimos confirmar tu acceso en Mininode.');
  }

  return response.json();
}

async function syncAuthState(session) {
  if (!session) {
    showSignedOut();
    return;
  }

  if (lastResolvedSessionId === session.id && !sessionPanel.hidden) return;

  showLoading('Confirmando tu acceso…');

  try {
    const identity = await resolveMininodeIdentity(session);
    lastResolvedSessionId = session.id;
    unmountSignIn();
    emailNode.textContent = identity.email || '';
    setVisible(loading, false);
    setVisible(signInNode, false);
    setVisible(errorPanel, false);
    setVisible(sessionPanel, true);
    setVisible(note, true);
  } catch (error) {
    showError(error instanceof Error ? error.message : 'No pudimos completar el acceso.');
  }
}

async function requestSync(session) {
  if (syncInFlight) {
    syncRequested = true;
    return;
  }

  syncInFlight = true;
  try {
    await syncAuthState(session);
  } finally {
    syncInFlight = false;
    if (syncRequested) {
      syncRequested = false;
      await requestSync(Clerk.session);
    }
  }
}

async function signOut() {
  showLoading('Cerrando sesión…');
  try {
    await Clerk.signOut();
  } catch {
    showError('No pudimos cerrar la sesión. Intenta nuevamente.');
  }
}

signOutButton.addEventListener('click', signOut);
errorSignOutButton.addEventListener('click', signOut);
retryButton.addEventListener('click', () => {
  lastResolvedSessionId = null;
  void requestSync(Clerk.session);
});

window.addEventListener('load', async () => {
  if (!window.Clerk || !window.__internal_ClerkUICtor) {
    showError('No pudimos cargar el servicio de acceso.');
    return;
  }

  try {
    await Clerk.load({
      ui: { ClerkUI: window.__internal_ClerkUICtor },
      localization,
      appearance: {
        variables: {
          colorPrimary: 'var(--color-primary)',
          colorText: 'var(--color-text)',
          colorTextSecondary: 'var(--color-muted)',
          colorBackground: 'transparent',
          colorInputBackground: 'var(--color-bg)',
          colorInputText: 'var(--color-text)',
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-body)',
        },
        options: {
          elevation: 'flush',
          socialButtonsPlacement: 'top',
          socialButtonsVariant: 'blockButton',
          privacyPageUrl: '/legal/privacy/',
        },
        elements: {
          rootBox: { width: '100%' },
          cardBox: {
            width: '100%',
            maxWidth: '100%',
            boxShadow: 'none',
            overflow: 'visible',
          },
          card: {
            width: '100%',
            boxShadow: 'none',
            border: '0',
            padding: '0',
            background: 'transparent',
          },
          header: { display: 'none' },
          footer: { display: 'none' },
          lastAuthenticationStrategyBadge: { display: 'none' },
          socialButtonsBlockButton: {
            minHeight: '46px',
            borderColor: 'var(--color-border)',
            color: 'var(--color-text)',
          },
          formFieldInput: {
            minHeight: '46px',
            borderColor: 'var(--color-border)',
          },
          formButtonPrimary: {
            minHeight: '46px',
            backgroundColor: 'var(--color-primary)',
            textTransform: 'none',
            fontWeight: '650',
          },
        },
      },
    });

    Clerk.addListener(({ session }) => {
      void requestSync(session);
    }, { skipInitialEmit: true });

    await requestSync(Clerk.session);
  } catch {
    showError('No pudimos iniciar el servicio de acceso. Intenta nuevamente.');
  }
});
