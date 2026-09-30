export const onRequestGet = async ({ request, env }) => {
  const publishableKey = env.CLERK_PUBLISHABLE_KEY || '';
  const hostname = new URL(request.url).hostname;

  if (!/^pk_(?:test|live)_/.test(publishableKey)) {
    return Response.json({ error: 'Clerk no configurado' }, {
      status: 503,
      headers: { 'Cache-Control': 'no-store' },
    });
  }

  if (hostname === 'app.mininode.io' && !publishableKey.startsWith('pk_live_')) {
    return Response.json({ error: 'Configuración Clerk de producción inválida' }, {
      status: 503,
      headers: { 'Cache-Control': 'no-store' },
    });
  }

  return Response.json({ publishableKey }, {
    headers: { 'Cache-Control': 'no-store' },
  });
};
