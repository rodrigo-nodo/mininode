# Mininode Backend (src/ layout)

FastAPI app packaged as `mininode_api` under `backend/src`.

## Endpoints
- `HEAD /` → 204 (probes)
- `GET /` → { status: "ok" }
- `GET /health`
- `POST /write/draft`
- `POST /analyze/summary`
- `POST /capture` (multipart)

## Requirements
- Python 3.11+
- Tesseract OCR instalado en el sistema (para `pytesseract`)
  - Debian/Ubuntu: `sudo apt-get install tesseract-ocr`
  - macOS (brew): `brew install tesseract`
  - Windows: instalar binario oficial y agregar a PATH
- Env vars opcionales:
  - `OPENAI_API_KEY` para llamadas reales (mini visión / fallback)
  - `API_KEY` o `API_KEYS` (coma-separado) para exigir `X-Api-Key`
  - `ALLOWED_ORIGINS` para CORS (coma-separado)

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # set OPENAI_API_KEY, API_KEY if needed
uvicorn mininode_api.main:app --app-dir backend/src --reload --port 8000
```

## cURL Examples

Health
```bash
curl -s http://localhost:8000/health | jq .
```

Write draft
```bash
curl -s -X POST http://localhost:8000/write/draft \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Write one paragraph about Mininode.","tone":"neutral"}' | jq .
```

Analyze summary (page)
```bash
curl -s -X POST http://localhost:8000/analyze/summary \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://example.com"],"scope":"page","lang":"en","prompt":"3-sentence summary"}' | jq .
```

Capture (file upload)
```bash
curl -s -X POST "http://localhost:8000/capture?doc_type=boleta&usar_fallback=true" \
  -H "X-Api-Key: $API_KEY" \
  -F "file=@/path/to/image.jpg" | jq .
```

### Respuesta Capture (resumen de campos)
- `fields`: diccionario de `FieldOut { value:str|null, confidence:float, source:str, uncertain:bool }`
- `consistency`: checks/notes previas al fallback (ej.: `total>=neto`)
- `consistency_after_fallback`: idem, recalculado tras aplicar fallback (si hubo ajustes)
- `timings` (ms): `{ ocr, llm_mini, llm_fallback, validate_ms, total }`
- `fallback_applied` (bool) y `adjusted_fields` (lista de críticos ajustados)

### Disparo de fallback
- Se activa si:
  - faltan campos críticos (según `CRITICAL_FIELDS` por `doc_type`), o
  - hay checks de consistencia fallidos, o
  - hay baja confianza (<0.6) en críticos detectada por OCR/anclas
- Nota: los valores del modelo se coercean a string al emitir `FieldOut`

Using X-Api-Key (if enabled)
```bash
curl -s -X POST http://localhost:8000/write/draft \
  -H "Content-Type: application/json" -H "X-Api-Key: $API_KEY" \
  -d '{"prompt":"Write one paragraph about Mininode.","tone":"neutral"}' | jq .
```

## Post‑Deploy Checks (Render)

Set your service base URL, e.g.: `API_BASE="https://<your-service>.onrender.com"`

```bash
# Health
curl -s "$API_BASE/health" | jq .

# Write (requires X-Api-Key if enforced)
curl -s -X POST "$API_BASE/write/draft" \
  -H "Content-Type: application/json" -H "X-Api-Key: $API_KEY" \
  -d '{"prompt":"Write one paragraph about Mininode.","tone":"neutral"}' | jq .

# Analyze (page)
curl -s -X POST "$API_BASE/analyze/summary" \
  -H "Content-Type: application/json" -H "X-Api-Key: $API_KEY" \
  -d '{"urls":["https://example.com"],"scope":"page","lang":"en","prompt":"3-sentence summary"}' | jq .

# Capture (file upload)
curl -s -X POST "$API_BASE/capture?doc_type=boleta&usar_fallback=true" \
  -H "X-Api-Key: $API_KEY" \
  -F "file=@/path/to/image.jpg" | jq .
```
