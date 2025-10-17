# Mininode (monorepo) – src/ layout

- `frontend/`: static site + functions (proxy)
- `backend/`: FastAPI app (`mininode_api`) under `backend/src`

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
MIT — ver archivo `LICENSE`. © 2025 Rodrigo.
