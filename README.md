# Mininode (monorepo) — Option B (src/ layout)

- `frontend/`: placeholder para landing/app
- `backend/`: FastAPI con layout `src/` → paquete `mininode_api`

## Backend local
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env && nano .env                       # agrega OPENAI_API_KEY si usarás LLM real
PYTHONPATH=./src uvicorn mininode_api.main:app --reload --app-dir backend/src
```
Pruebas rápidas:
```bash
curl http://localhost:8000/health
curl -s -X POST http://localhost:8000/write/draft   -H 'Content-Type: application/json'   -d '{"prompt":"Write one paragraph about Mininode.","tone":"neutral"}'

curl -s -X POST http://localhost:8000/capture/parse   -H 'Content-Type: application/json'   -d '{"image_b64":"dGVzdA==","save":false}'

curl -s -X POST http://localhost:8000/analyze/summary   -H 'Content-Type: application/json'   -d '{"urls":["https://example.com"],"scope":"page","lang":"en","prompt":"3-sentence summary"}'
```
