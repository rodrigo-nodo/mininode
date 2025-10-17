# Mininode Backend (src/ layout)

FastAPI app packaged as `mininode_api` under `backend/src`.

## Endpoints
- `GET /health`
- `POST /write/draft`
- `POST /analyze/summary`
- `POST /capture`

## Requirements
- Python 3.11+
- Optional env vars:
  - `OPENAI_API_KEY` for real LLM calls
  - `API_KEY` or `API_KEYS` (comma-separated) to enforce `X-Api-Key` on endpoints

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

Using X-Api-Key (if enabled)
```bash
curl -s -X POST http://localhost:8000/write/draft \
  -H "Content-Type: application/json" -H "X-Api-Key: $API_KEY" \
  -d '{"prompt":"Write one paragraph about Mininode.","tone":"neutral"}' | jq .
```
