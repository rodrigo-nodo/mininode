# Mininode (monorepo) — Option B (src/ layout)

- `frontend/`: placeholder para landing/app
- `backend/`: FastAPI con layout `src/` → paquete `mininode_api`

## Backend local
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env && nano .env                       # agrega OPENAI_API_KEY si usarás LLM real
PYTHONPATH=./src uvicorn app:app --reload
```
Pruebas rápidas:
```bash
curl http://localhost:8000/health
curl -s -X POST http://localhost:8000/redaccion/draft   -H 'Content-Type: application/json'   -d '{"prompt":"Escribe 1 párrafo sobre Mininode.","tone":"cercano"}'

curl -s -X POST http://localhost:8000/image2json/parse   -H 'Content-Type: application/json'   -d '{"image_b64":"dGVzdA==","save":false}'
```
