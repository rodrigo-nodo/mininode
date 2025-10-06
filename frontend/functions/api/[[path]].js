export const onRequest = async (ctx) => {
  const { request, env } = ctx;
  const url = new URL(request.url);

  // Responder preflight (por si el navegador hace OPTIONS)
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

  // Ruta pública después de /api/
  const destPathPublic = url.pathname.replace(/^\/api\/?/, '');

  // Whitelist MVP (evita open-proxy)
  const ALLOWED = new Set([
    'write/draft',
  ]);
  if (!ALLOWED.has(destPathPublic)) {
    return new Response(JSON.stringify({ error: 'Path no permitido', path: destPathPublic }), {
      status: 403,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }

  // Mapeo público -> backend legacy
  const ROUTE_MAP = {
    'write/draft': 'redaccion/draft',
  };
  const destPathBackend = ROUTE_MAP[destPathPublic] || destPathPublic;

  // Validar Secrets/Vars
  const apiKey  = env.MININODE_API_KEY; // SECRET
  const apiBase = env.MININODE_API_BASE || 'https://api.mininode.io';
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'Falta MININODE_API_KEY en env (Pages Secrets)' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }

  // Construir URL destino
  const target = new URL(`${apiBase}/${destPathBackend}`);
  target.search = url.search;

  // Leer body como TEXTO (más compatible con FastAPI)
  const method = request.method.toUpperCase();
  const hasBody = !['GET', 'HEAD'].includes(method);
  const bodyText = hasBody ? await request.text() : undefined;

  // Headers hacia backend
  const headers = new Headers();
  headers.set('Content-Type', request.headers.get('Content-Type') || 'application/json');
  headers.set('X-Api-Key', apiKey);

  try {
    const upstream = await fetch(target.toString(), {
      method,
      headers,
      body: bodyText,
    });

    // Pasar status y body tal cual; preservar Content-Type
    const outHeaders = new Headers();
    outHeaders.set('Content-Type', upstream.headers.get('Content-Type') || 'application/json');
    outHeaders.set('Access-Control-Allow-Origin', '*');

    const upstreamBody = await upstream.text();
    return new Response(upstreamBody, { status: upstream.status, headers: outHeaders });
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Proxy error', detail: String(e) }), {
      status: 502,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    });
  }
};
