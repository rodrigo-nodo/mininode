# Mininode Frontend

Static site + small API proxy to talk to the backend. Uses English-only routes.

## Overview
- Páginas clave:
  - Home: `frontend/index.html`
  - Agents: `frontend/agents/index.html` y `frontend/agents/write/index.html`
  - SaaS Capture: `frontend/saas/capture/index.html`
- Lógica UI:
  - Escritura: `frontend/assets/js/write.page.js`
  - Capture: `frontend/assets/js/capture.page.js`
- Proxy Functions: `frontend/functions/api/[[path]].js`

## Local Development
- Servidor estático sencillo
  - `npx http-server ./frontend -p 4173` (o `python -m http.server` en `frontend/`)
- Backend
  - Inicia la API en `http://localhost:8000` (ver backend/README.md).

## Head común y rutas relativas
- `partials/head-common.html` se inyecta vía `assets/js/core-head.js` (favicons/meta centralizados)
- `include.js` normaliza rutas de `header/footer` usando atributos `data-rel` (funciona con file://)

## Environment Variables
- `MININODE_API_BASE`: URL base del backend (Render). El front también la usa directamente cuando corre como file://; si no se define, usa `/api` (proxy) en producción.
- `MININODE_API_KEY`: secret en Pages; el proxy lo reenvía como `X-Api-Key` al backend.
- Defínelas en Cloudflare Pages → Project → Settings → Environment Variables / Secrets.

## API Proxy (Functions)
- Ruta: `frontend/functions/api/[[path]].js`.
- Lista blanca: `ALLOWED`.
- Mapping público → backend: `ROUTE_MAP`.
- Rutas actuales: `write/draft`, `analyze/summary`, `capture`.
- Maneja CORS y soporta `multipart/form-data` (reenvía el stream con boundary intacto).

## Write Page
- Ubicación: `frontend/agents/write/index.html` con lógica en `frontend/assets/js/write.page.js`.
- Endpoints usados (vía proxy): `/api/write/draft`, `/api/analyze/summary`.
- Notas:
  - Borrador local funciona sin backend.
  - El análisis de URLs requiere backend/API key para resultados reales.

## Capture (UI)
- Formatos: `jpg`, `jpeg`, `png` (≤ 5 MB). `webp` se convierte en cliente. `heic/heif` bloqueado con aviso.
- Feedback inmediato al elegir/soltar: miniatura, nombre, tamaño; botón se habilita.
- Badge: `Total Xs | p95(sess) Ys` (p95 local de la sesión del navegador).
- Differences: checks fallidos antes/después y campos ajustados cuando hay fallback.
- Flujo backend (Fase 1): 4o-first (cabecera) → preprocesado ligero → OCR + anclas → combinación y validación → fallback si aplica.

## Run With Proxy Locally
- Con Cloudflare Pages Functions:
  - `wrangler pages dev frontend` para correr estático + functions.
  - Define `MININODE_API_BASE` y `MININODE_API_KEY` si el backend exige auth.

## Build & Deploy
- Estático: deploy `frontend/` en tu host.
- Functions: deploy `frontend/functions` (Cloudflare Pages Functions).
- Verifica tras el deploy: `POST /api/write/draft`, `POST /api/analyze/summary`, `POST /api/capture`.

## Troubleshooting
- 403 desde proxy: revisa `ALLOWED` y `ROUTE_MAP`.
- 401 desde backend: `MININODE_API_KEY` no coincide.
- 404 al usar `/api/*` en file://: el front ya usa `MININODE_API_BASE` automáticamente; define `MININODE_API_BASE` o ejecuta con Pages dev.
- Mixed content: usa HTTPS para sitio y API en producción.

## Testing Proxy (cURL)
- Write draft: `curl -s -X POST "https://<your-site>/api/write/draft" -H "Content-Type: application/json" -d '{"prompt":"Write one paragraph about Mininode.","tone":"neutral"}'`
- Analyze summary: `curl -s -X POST "https://<your-site>/api/analyze/summary" -H "Content-Type: application/json" -d '{"urls":["https://example.com"],"scope":"page","lang":"en","prompt":"3-sentence summary"}'`
- Capture: `curl -s -X POST "https://<your-site>/api/capture?doc_type=boleta&usar_fallback=true" -F "file=@/path/to/image.jpg"`
