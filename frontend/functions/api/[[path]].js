export const onRequest = async (ctx) => {
  const { request, env } = ctx;
  const url = new URL(request.url);

  // OPTIONS (CORS preflight)
  if (request.method.toUpperCase() === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
      },
    });
  }

  const destPathPublic = url.pathname.replace(/^\/api\/?/, '');

  // Whitelist MVP
  const ALLOWED = new Set(['write/draft', 'analyze/summary', 'capture', 'privacy/diagnose', 'learn/feedback']);
  const isFeedbackUpdate = /^learn\/feedback\/[0-9a-f-]+$/.test(destPathPublic);
  if (!ALLOWED.has(destPathPublic) && !isFeedbackUpdate) {
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
  const destPathBackend = ROUTE_MAP[destPathPublic] || destPathPublic;

  const apiBase = env.MININODE_API_BASE || 'https://api.mininode.io';
  const target = new URL(`${apiBase}/${destPathBackend}`);
  target.search = url.search;

  const method = request.method.toUpperCase();

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
  headers.set('X-Api-Key', env.MININODE_API_KEY || '');

  if (!env.MININODE_API_KEY) {
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
