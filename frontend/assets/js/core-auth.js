(function () {
  'use strict';

  // Access owns its Clerk lifecycle. Privacy Web already loads Clerk because
  // authenticated diagnostics need a token, so it also owns that lifecycle.
  const path = window.location.pathname || '/';
  if (path.startsWith('/access') || path.startsWith('/privacy/')) return;

  let clerkReady = null;

  async function loadClerk() {
    if (window.Clerk) return window.Clerk;
    if (clerkReady) return clerkReady;

    clerkReady = (async () => {
      const response = await fetch('/clerk-config', {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      });
      if (!response.ok) throw new Error('Clerk configuration unavailable');

      const { publishableKey } = await response.json();
      if (typeof publishableKey !== 'string' || !/^pk_(?:test|live)_/.test(publishableKey)) {
        throw new Error('Invalid Clerk configuration');
      }
      if (window.location.hostname === 'app.mininode.io' && !publishableKey.startsWith('pk_live_')) {
        throw new Error('Development Clerk configuration rejected in production');
      }

      const encoded = publishableKey.split('_')[2];
      const domain = encoded ? atob(encoded).slice(0, -1) : '';
      if (!domain || !/^[a-z0-9.-]+$/i.test(domain)) throw new Error('Invalid Clerk domain');

      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://' + domain + '/npm/@clerk/clerk-js@6/dist/clerk.browser.js';
        script.async = true;
        script.crossOrigin = 'anonymous';
        script.setAttribute('data-clerk-publishable-key', publishableKey);
        script.addEventListener('load', resolve, { once: true });
        script.addEventListener('error', () => reject(new Error('Clerk runtime unavailable')), { once: true });
        document.head.appendChild(script);
      });

      await window.Clerk.load();
      return window.Clerk;
    })();

    return clerkReady;
  }

  function syncHeader(signedIn) {
    const accessLink = document.querySelector('#header-access-link');
    const signOut = document.querySelector('#header-sign-out');
    if (!accessLink || !signOut) return;

    accessLink.hidden = signedIn;
    signOut.hidden = !signedIn;

    if (signedIn && signOut.dataset.authBound !== 'true') {
      signOut.dataset.authBound = 'true';
      signOut.addEventListener('click', async () => {
        try {
          await window.Clerk?.signOut();
        } finally {
          window.location.assign('/');
        }
      });
    }
  }

  async function initialize() {
    try {
      const clerk = await loadClerk();
      syncHeader(Boolean(clerk.session));
      clerk.addListener(({ session }) => syncHeader(Boolean(session)), { skipInitialEmit: true });
    } catch (_error) {
      // Public pages remain usable when auth status cannot be resolved.
      syncHeader(false);
    }
  }

  window.addEventListener('mininode:includes-loaded', initialize, { once: true });
  if (document.querySelector('#header-access-link')) initialize();
}());
