export const onRequest = ({ request, env }) => {
  const pageUrl = new URL(request.url);
  pageUrl.pathname = '/privacy/plan/index.html';
  pageUrl.search = '';
  return env.ASSETS.fetch(pageUrl);
};
