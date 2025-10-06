export const onRequest = async (ctx) => {
  const { request, env } = ctx;
  const url = new URL(request.url);

  // 1) resolver path destino (lo que va después de /api/)
  const destPath = url.pathname.replace(/^\/api\/?/, "");

  // 2) whitelist simple para MVP (evita open-proxy)
  const ALLOWED = new Set([
    "write/draft", // ← hoy solo este; agrega más cuando habilites otros agentes
    // "legal/summary",
    // "accounting/ledger",
  ]);
  if (!ALLOWED.has(destPath)) {
    return new Response(JSON.stringify({ error: "Path no permitido", path: destPath }), {
      status: 403,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 3) construir URL objetivo usando tus env vars
  const apiBase = env.MININODE_API_BASE || "https://api.mininode.io";
  const target = new URL(`${apiBase}/${destPath}`);
  target.search = url.search;

  // 4) preparar request hacia el backend
  const method = request.method.toUpperCase();
  const hasBody = !["GET", "HEAD"].includes(method);
  const body = hasBody ? await request.arrayBuffer() : undefined;

  const headers = new Headers();
  headers.set("Content-Type", request.headers.get("Content-Type") || "application/json");
  headers.set("X-Api-Key", env.MININODE_API_KEY); // ← SECRET en Pages

  try {
    const upstream = await fetch(target.toString(), { method, headers, body });

    // 5) reenviar respuesta al cliente (sin exponer headers sensibles)
    const outHeaders = new Headers();
    outHeaders.set("Content-Type", upstream.headers.get("Content-Type") || "application/json");
    // CORS simple (ajústalo si usarás cookies/sesiones):
    outHeaders.set("Access-Control-Allow-Origin", "*");

    return new Response(upstream.body, { status: upstream.status, headers: outHeaders });
  } catch (e) {
    return new Response(JSON.stringify({ error: "Proxy error", detail: String(e) }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
};
