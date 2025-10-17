# Mininode Frontend

Static site + small API proxy to talk to the backend. Uses English-only routes.

## Overview
- Key files:
  - `frontend/index.html` and pages under `frontend/agents/*`
  - `frontend/assets/js/write.page.js` (writer UI logic)
  - `frontend/functions/api/[[path]].js` (proxy function)

## Local Development
- Simple static server
  - `npx http-server ./frontend -p 4173` (or `python -m http.server` in `frontend/`)
- Backend
  - Start API at `http://localhost:8000` (see backend/README.md).

## Environment Variables
- `MININODE_API_BASE`: backend base URL (default `https://api.mininode.io`).
- `MININODE_API_KEY`: API key forwarded to backend as `X-Api-Key` by the proxy.
- On Cloudflare Pages, define them under Project → Settings → Environment Variables / Secrets.

## API Proxy (Functions)
- Path: `frontend/functions/api/[[path]].js`.
- Whitelist: update `ALLOWED` to permit public routes.
- Mapping: update `ROUTE_MAP` for public → backend paths.
- Current allowed/mapped routes:
  - `write/draft`
  - `analyze/summary`
  - `capture`
- Handles CORS preflight and JSON pass-through.

## Write Page
- Location: `frontend/agents/write/index.html` with logic in `frontend/assets/js/write.page.js`.
- Endpoints used:
  - Draft: `POST /api/write/draft`
  - Analyze (proxy first): `POST /api/analyze/summary`
  - Analyze (direct fallback URL): `https://api.mininode.io/analyze/summary`
- Notes:
  - Local draft fallback works without backend.
  - URL analysis is best-effort; requires backend/API key for real output.

## Run With Proxy Locally
- With Cloudflare Pages Functions:
  - `wrangler pages dev frontend` to run static + functions together.
  - Set `MININODE_API_BASE` and `MININODE_API_KEY` for local dev if backend requires auth.

## Build & Deploy
- Static files: deploy `frontend/` to your static host.
- Functions: deploy `frontend/functions` with your platform (e.g., Cloudflare Pages Functions).
- Verify these routes after deploy:
  - `POST /api/write/draft`
  - `POST /api/analyze/summary`
  - `POST /api/capture`

## Troubleshooting
- 403 from proxy: ensure route is in `ALLOWED` and `ROUTE_MAP` is correct.
- 401 from backend: set `MININODE_API_KEY` to match API server config.
- Mixed content errors: use HTTPS for both site and API in production.
