(function () {
  'use strict';

  if (window.MininodeAuth) return;

  let configPromise = null;
  let readyPromise = null;
  let initializedWithUi = false;
  let currentSession = null;
  let providerListenerBound = false;
  const subscribers = new Set();

  function loadScript(src, attributes = {}) {
    const existing = Array.from(document.scripts).find((script) => script.src === src);
    if (existing) {
      if (existing.dataset.loaded === 'true') return Promise.resolve();
      return new Promise((resolve, reject) => {
        existing.addEventListener('load', resolve, { once: true });
        existing.addEventListener('error', () => reject(new Error('Authentication runtime unavailable')), { once: true });
      });
    }

    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.crossOrigin = 'anonymous';
      for (const [name, value] of Object.entries(attributes)) script.setAttribute(name, value);
      script.addEventListener('load', () => {
        script.dataset.loaded = 'true';
        resolve();
      }, { once: true });
      script.addEventListener('error', () => reject(new Error('Authentication runtime unavailable')), { once: true });
      document.head.appendChild(script);
    });
  }

  async function loadConfig() {
    if (configPromise) return configPromise;
    configPromise = (async () => {
      const response = await fetch('/clerk-config', {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      });
      if (!response.ok) throw new Error('Authentication configuration unavailable');

      const { publishableKey } = await response.json();
      if (typeof publishableKey !== 'string' || !/^pk_(?:test|live)_/.test(publishableKey)) {
        throw new Error('Invalid authentication configuration');
      }
      if (window.location.hostname === 'app.mininode.io' && !publishableKey.startsWith('pk_live_')) {
        throw new Error('Development authentication configuration rejected in production');
      }

      const encoded = publishableKey.split('_')[2];
      const domain = encoded ? atob(encoded).slice(0, -1) : '';
      if (!domain || !/^[a-z0-9.-]+$/i.test(domain)) throw new Error('Invalid authentication domain');
      return { publishableKey, domain };
    })();
    return configPromise;
  }

  function syncHeader(signedIn) {
    const control = document.querySelector('#header-auth-control');
    if (!control) return;

    control.dataset.authState = signedIn ? 'signed-in' : 'signed-out';
    control.textContent = signedIn ? 'Cerrar sesión' : 'Acceder';
    control.setAttribute('aria-label', signedIn ? 'Cerrar sesión' : 'Acceder a Mininode');
    control.removeAttribute('title');

    if (control.dataset.authBound !== 'true') {
      control.dataset.authBound = 'true';
      control.addEventListener('click', async (event) => {
        if (!api.isSignedIn()) return;
        event.preventDefault();
        try {
          await api.signOut();
          window.location.assign('/');
        } catch (_error) {
          syncHeader(Boolean(currentSession));
          control.textContent = 'Reintentar cierre';
          control.setAttribute('aria-label', 'No se pudo cerrar sesión. Intenta nuevamente.');
          control.title = 'No se pudo cerrar sesión. Intenta nuevamente.';
        }
      });
    }
  }

  function publish(session) {
    currentSession = session || null;
    const state = { session: currentSession, signedIn: Boolean(currentSession) };
    syncHeader(state.signedIn);
    subscribers.forEach((listener) => {
      try { listener(state); } catch (_error) { /* subscriber isolation */ }
    });
  }

  function bindProviderListener() {
    if (providerListenerBound) return;
    window.Clerk.addListener(({ session }) => publish(session), { skipInitialEmit: true });
    providerListenerBound = true;
  }

  async function initialize(options = {}) {
    const withUi = options.ui === true;
    const { publishableKey, domain } = await loadConfig();

    if (withUi) {
      await loadScript('https://' + domain + '/npm/@clerk/ui@1/dist/ui.browser.js');
    }
    await loadScript(
      'https://' + domain + '/npm/@clerk/clerk-js@6/dist/clerk.browser.js',
      { 'data-clerk-publishable-key': publishableKey },
    );

    if (!window.Clerk) throw new Error('Authentication runtime unavailable');
    if (withUi && !window.__internal_ClerkUICtor) throw new Error('Authentication UI unavailable');

    const loadOptions = withUi
      ? { ui: { ClerkUI: window.__internal_ClerkUICtor }, ...(options.localization ? { localization: options.localization } : {}) }
      : {};
    await window.Clerk.load(loadOptions);
    initializedWithUi = withUi;
    bindProviderListener();
    publish(window.Clerk.session);
    return api;
  }

  async function ready(options = {}) {
    const wantsUi = options.ui === true;
    if (readyPromise) {
      await readyPromise;
      if (wantsUi && !initializedWithUi) {
        throw new Error('Authentication was initialized without UI support');
      }
      syncHeader(Boolean(currentSession));
      return api;
    }
    readyPromise = initialize(options);
    try {
      const result = await readyPromise;
      syncHeader(Boolean(currentSession));
      return result;
    } catch (error) {
      readyPromise = null;
      throw error;
    }
  }

  const api = {
    ready,
    isSignedIn() {
      return Boolean(currentSession);
    },
    session() {
      return currentSession;
    },
    async getToken() {
      await ready();
      return currentSession?.getToken ? currentSession.getToken() : null;
    },
    async signOut() {
      await ready();
      await window.Clerk.signOut();
    },
    subscribe(listener, options = {}) {
      if (typeof listener !== 'function') return () => {};
      subscribers.add(listener);
      if (options.emitCurrent !== false) {
        listener({ session: currentSession, signedIn: Boolean(currentSession) });
      }
      return () => subscribers.delete(listener);
    },
    mountSignIn(node, options = {}) {
      if (!initializedWithUi || !window.Clerk?.mountSignIn) {
        throw new Error('Authentication UI is not ready');
      }
      window.Clerk.mountSignIn(node, options);
    },
    unmountSignIn(node) {
      if (window.Clerk?.unmountSignIn) window.Clerk.unmountSignIn(node);
    },
  };

  window.MininodeAuth = api;
  window.dispatchEvent(new CustomEvent('mininode:auth-api-ready'));

  function bindHeaderWhenAvailable() {
    if (!document.querySelector('#header-auth-control')) return false;
    syncHeader(Boolean(currentSession));
    return true;
  }

  window.addEventListener('mininode:includes-loaded', bindHeaderWhenAvailable);
  const observer = new MutationObserver(() => {
    if (bindHeaderWhenAvailable()) observer.disconnect();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  const requiresAuthUi = document.body?.dataset.mininodeAuthUi === 'clerk';
  if (!requiresAuthUi) {
    void ready().catch(() => {
      publish(null);
    });
  }
}());
