export const onRequest = ({ request, env }) => {
  const requestUrl = new URL(request.url);
  const isPlanPath = /^\/privacy\/plan\/[A-Za-z0-9_-]+\/?$/.test(requestUrl.pathname);

  if (!isPlanPath) return env.ASSETS.fetch(request);

  // Fetch the directory URL so Pages resolves its index document internally.
  // Requesting index.html directly is canonicalized by Pages' HTML handling.
  const pageUrl = new URL(request.url);
  pageUrl.pathname = '/privacy/plan/';
  pageUrl.search = '';
  return env.ASSETS.fetch(pageUrl);
};
