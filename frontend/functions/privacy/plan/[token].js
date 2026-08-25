export const onRequest = ({ request, env }) => {
  const requestUrl = new URL(request.url);
  const isPlanPath = /^\/privacy\/plan\/[A-Za-z0-9_-]+\/?$/.test(requestUrl.pathname);

  if (!isPlanPath) return env.ASSETS.fetch(request);

  const pageUrl = new URL(request.url);
  pageUrl.pathname = '/privacy/plan/index.html';
  pageUrl.search = '';
  return env.ASSETS.fetch(pageUrl);
};
