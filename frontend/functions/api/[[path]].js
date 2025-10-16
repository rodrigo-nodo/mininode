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
  const ALLOWED = new Set(['write/draft', 'analyze/summary', 'capture/parse']);
  if (!ALLOWED.has(destPathPublic)) {
    return new Response(JSON.stringify({ error: 'Path no permitido', path: destPathPublic }), {
      status: 403,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }

  // Public -> backend mapping (backend uses English-only routes)
  const ROUTE_MAP = {
    'write/draft': 'write/draft',
    'analyze/summary': 'analyze/summary',
    'capture/parse': 'capture/parse',
  };
  const destPathBackend = ROUTE_MAP[destPathPublic] || destPathPublic;

  const apiBase = env.MININODE_API_BASE || 'https://api.mininode.io';
  const target = new URL(`${apiBase}/${destPathBackend}`);
  target.search = url.search;

  const method = request.method.toUpperCase();

  // --- LECTURA Y NORMALIZACIÓN DEL BODY ---
  let bodyText = '';
  let contentType = request.headers.get('Content-Type') || 'application/json';
  if (!['GET', 'HEAD'].includes(method)) {
    bodyText = await request.text(); // leer como texto

    // Si es JSON, valida y re-serializa
    if (contentType.includes('application/json')) {
      try {
        const obj = bodyText ? JSON.parse(bodyText) : {};
        // TIP: asegúrate de que prompt y tone viajen
        bodyText = JSON.stringify(obj);
      } catch (e) {
        return new Response(JSON.stringify({ error: 'JSON inválido', detail: String(e), body: bodyText }), {
          status: 400,
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        });
      }
    }
  }

  // Headers hacia backend
  const headers = new Headers();
  headers.set('Content-Type', contentType);
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
      body: ['GET', 'HEAD'].includes(method) ? undefined : bodyText,
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
