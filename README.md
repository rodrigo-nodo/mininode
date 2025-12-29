# Mininode (monorepo)

- `frontend/`: sitio estático + Functions (proxy) y UI (Agents/SaaS) 
  - html + css + js
- `backend/`: FastAPI app (`mininode_api`) bajo `backend/src`
  - python + postgreSQL

## Novedades relevantes (MVP Capture)
- Front Capture (SaaS): `frontend/saas/capture/index.html`
  - Drag & drop + selección; feedback inmediato (miniatura, nombre, tamaño)
  - Soporta `jpg`, `jpeg`, `png`; `webp` se convierte en cliente; `heic/heif` bloqueado con mensaje
  - Badge de rendimiento: `Total Xs | p95(sess) Ys` (p95 local de sesión del navegador)
- Head común y rutas relativas
  - Head centralizado en `partials/head-common.html`, inyectado por `assets/js/core-head.js`
  - `include.js` normaliza enlaces `[data-rel]` de header/footer según profundidad (funciona con file:// y estáticos)
- Proxy `/api/*` con multipart (Cloudflare Pages Functions): `frontend/functions/api/[[path]].js`
  - Reenvía adjuntos sin tocar el boundary; requiere `MININODE_API_KEY` si el backend valida API key
- Backend Capture: 4o-first, preprocesado y fallback
  - Orden de pipeline: 4o-first (cabecera) → preprocesado ligero → OCR + anclas (ROI lógico) → combinación → validación → fallback si aplica
  - `TimingMs.validate` renombrado a `validate_ms` (evita warning Pydantic)
  - Nuevos campos: `fallback_applied`, `adjusted_fields`, `consistency_after_fallback`
  - `timings.llm_fallback` ahora mide el tiempo real del fallback
  - `timings.llm_mini` refleja el tiempo del paso LLM de cabecera (4o-first)

## Backend Quickstart
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env                   # set OPENAI_API_KEY / API_KEY as needed
uvicorn mininode_api.main:app --app-dir backend/src --reload --port 8000
```

Common cURL
```bash
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/write/draft \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Write one paragraph about Mininode.","tone":"neutral"}'
curl -s -X POST "http://localhost:8000/capture?doc_type=boleta&usar_fallback=true" \
  -H 'X-Api-Key: '$API_KEY \
  -F "file=@/path/to/image.jpg"
curl -s -X POST http://localhost:8000/analyze/summary \
  -H 'Content-Type: application/json' \
  -d '{"urls":["https://example.com"],"scope":"page","lang":"en","prompt":"3-sentence summary"}'
```

See more details in `backend/README.md`.

## Licencia
MIT – ver archivo `LICENSE`. © 2025 Rodrigo.



## Anexo:
### Subdominios
Se define usar subdominios por cada servicio (saas1.mininode.io) en vez de rutas mininode.io/saas1 (subruta):

saas1.mininode.io (subdominio):
- Aisla cachés, cookies y CORS; DNS y certificados separados.
- Despliegues más independientes; cada Pages/Worker puede tener su dominio.
- URLs limpias y evitas colisiones de rutas/estáticos entre apps.

mininode.io/saas1 (subruta):
- Un solo dominio/certificado; puede simplificar marketing/SEO.
- Necesitas un router/rewrite en Cloudflare que sirva cada app por carpeta, y cuidar paths relativos de assets.
- Cookies/caché se comparten si no las segmentas.
