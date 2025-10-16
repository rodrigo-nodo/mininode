# Mininode Backend (src/ layout)

- Endpoints:
  - `GET /health`
  - `POST /write/draft`
  - `POST /capture/parse`
  - `POST /analyze/summary`

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=./src uvicorn mininode_api.main:app --reload --app-dir backend/src
```
