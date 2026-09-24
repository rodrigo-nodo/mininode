export const onRequest = async (ctx) => {
  const { request, env } = ctx;
  const url = new URL(request.url);
  const method = request.method.toUpperCase();

  // OPTIONS (CORS preflight)
  if (method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE,OPTIONS',
      },
    });
  }

  // Match only the pathname: the query is forwarded below, but never participates
  // in the allowlist. Pages routes this function below /api, so normalize that
  // boundary (and an optional trailing slash) once before applying strict matches.
  const pathWithoutApi = url.pathname.replace(/^\/+api(?:\/+|$)/, '');
  const destPathPublic = pathWithoutApi.replace(/^\/+|\/+$/g, '');

  // Whitelist MVP
  const ALLOWED = new Set(['write/draft', 'analyze/summary', 'capture', 'privacy/diagnose', 'learn/feedback']);
  // Security for browser-facing plan routes is based on the HTTP pathname itself,
  // never on a catch-all parameter or a reconstructed path.
  const isCorrectionPlan = /^\/api\/privacy\/correction-plans\/[A-Za-z0-9_-]+\/?$/.test(url.pathname);
  const isCorrectionPlanCheck = /^\/api\/privacy\/correction-plans\/[A-Za-z0-9_-]+\/check\/?$/.test(url.pathname);
  const isAllowedCorrectionPlan = (isCorrectionPlan && method === 'GET')
    || (isCorrectionPlanCheck && method === 'POST');
  const isPublicOrderCreation = destPathPublic === 'privacy/correction-plan-orders'
    && method === 'POST';
  const isFeedbackById = /^learn\/feedback\/[0-9a-f-]+$/.test(destPathPublic);
  const isAllowedFeedbackById = isFeedbackById && ['GET', 'PATCH'].includes(method);
  const isPrivacyData = /^privacy\/data\/(catalog|maps(?:\/[A-Za-z0-9_-]+(?:\/(?:activities(?:\/[0-9a-f-]+)?|recovery-link))?)?)$/.test(destPathPublic);
  const isAllowedPrivacyData = isPrivacyData && ['GET', 'POST', 'PATCH', 'DELETE'].includes(method);
  const isPrivacyDataReview = /^privacy\/data\/maps\/[A-Za-z0-9_-]+\/review$/.test(destPathPublic);
  const isAllowedPrivacyDataReview = isPrivacyDataReview && method === 'GET';
  if (!ALLOWED.has(destPathPublic) && !isAllowedFeedbackById && !isAllowedCorrectionPlan && !isPublicOrderCreation && !isAllowedPrivacyData && !isAllowedPrivacyDataReview) {
    return new Response(JSON.stringify({ error: 'Path no permitido', path: destPathPublic }), {
      status: 403,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }

  // Public -> backend mapping (backend uses English-only routes)
  const ROUTE_MAP = {
    'write/draft': 'write/draft',
    'analyze/summary': 'analyze/summary',
    'capture': 'capture',
    'privacy/diagnose': 'privacy/diagnose',
    'learn/feedback': 'learn/feedback',
  };
  const correctionPlanBackendPath = url.pathname
    .replace(/^\/api\//, '')
    .replace(/\/$/, '');
  const destPathBackend = isAllowedCorrectionPlan
    ? correctionPlanBackendPath
    : (ROUTE_MAP[destPathPublic] || destPathPublic);

  const apiBase = env.MININODE_API_BASE || 'https://api.mininode.io';
  const target = new URL(`${apiBase}/${destPathBackend}`);
  target.search = url.search;

  // --- LECTURA Y NORMALIZACIÓN DEL BODY ---
  const origContentType = request.headers.get('Content-Type') || '';
  let body = undefined;
  let contentType = origContentType || 'application/json';
  if (!['GET', 'HEAD'].includes(method)) {
    if (origContentType.includes('multipart/form-data')) {
      // No tocar el cuerpo; forward stream (boundary debe preservarse)
      body = request.body;
    } else if (origContentType.includes('application/json')) {
      const txt = await request.text();
      try {
        const obj = txt ? JSON.parse(txt) : {};
        body = JSON.stringify(obj);
      } catch (e) {
        return new Response(JSON.stringify({ error: 'JSON inválido', detail: String(e) }), {
          status: 400,
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        });
      }
    } else {
      // Otros (texto simple, etc.)
      body = await request.text();
    }
  }

  // Headers hacia backend
  const headers = new Headers();
  if (contentType) headers.set('Content-Type', contentType);
  headers.set('Accept', 'application/json');
  if (!isAllowedCorrectionPlan && !isPublicOrderCreation && !isAllowedPrivacyData && !isAllowedPrivacyDataReview && !isAccessIdentity) headers.set('X-Api-Key', env.MININODE_API_KEY || '');
  if (isAccessIdentity) {
    const accessAssertion = request.headers.get('Cf-Access-Jwt-Assertion');
    if (accessAssertion) headers.set('Cf-Access-Jwt-Assertion', accessAssertion);
  }

  if (!isAllowedCorrectionPlan && !isPublicOrderCreation && !isAllowedPrivacyData && !isAllowedPrivacyDataReview && !isAccessIdentity && !env.MININODE_API_KEY) {
    return new Response(JSON.stringify({ error: 'Falta MININODE_API_KEY (Pages Secret)' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }

  try {
    const upstream = await fetch(target.toString(), {
      method,
      headers,
      body: ['GET', 'HEAD'].includes(method) ? undefined : body,
    });

    const upstreamBody = await upstream.text();
    const outHeaders = new Headers();
    outHeaders.set('Content-Type', upstream.headers.get('Content-Type') || 'application/json');
    outHeaders.set('Access-Control-Allow-Origin', '*');

    // Pasa tal cual la respuesta del backend (incluido el detalle de 4xx/5xx)
    return new Response(upstreamBody, { status: upstream.status, headers: outHeaders });
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Proxy error', detail: String(e) }), {
      status: 502,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }
};
