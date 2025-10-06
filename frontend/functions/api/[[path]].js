export const onRequest = async (ctx) => {
  const { request, env } = ctx;
  const url = new URL(request.url);

  // 1) destPath público (lo que viene después de /api/)
  const destPathPublic = url.pathname.replace(/^\/api\/?/, "");

  // 2) Whitelist (público)
  const ALLOWED = new Set([
    "write/draft",
    // agrega otros cuando existan
  ]);
  if (!ALLOWED.has(destPathPublic)) {
    return new Response(JSON.stringify({ error: "Path no permitido", path: destPathPublic }), {
      status: 403, headers: { "Content-Type": "application/json" },
    });
  }

  // 3) Traducción público -> backend (routing interno)
  const ROUTE_MAP = {
    "write/draft": "redaccion/draft",   // 👈 mapea a tu backend actual
    // "write/export/docx": "redaccion/export/docx",
  };
  const destPathBackend = ROUTE_MAP[destPathPublic] || destPathPublic;

  const apiBase = env.MININODE_API_BASE || "https://api.mininode.io";
  const target = new URL(`${apiBase}/${destPathBackend}`);
  target.search = url.search;

  const method = request.method.toUpperCase();
  const hasBody = !["GET", "HEAD"].includes(method);
  const body = hasBody ? await request.arrayBuffer() : undefined;

  const headers = new Headers();
  headers.set("Content-Type", request.headers.get("Content-Type") || "application/json");
  headers.set("X-Api-Key", env.MININODE_API_KEY);

  try {
    const upstream = await fetch(target.toString(), { method, headers, body });
    const out = new Headers();
    out.set("Content-Type", upstream.headers.get("Content-Type") || "application/json");
    out.set("Access-Control-Allow-Origin", "*");
    return new Response(upstream.body, { status: upstream.status, headers: out });
  } catch (e) {
    return new Response(JSON.stringify({ error: "Proxy error", detail: String(e) }), {
      status: 502, headers: { "Content-Type": "application/json" },
    });
  }
};
