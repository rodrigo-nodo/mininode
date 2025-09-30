# Mininode Backend (src/ layout)

- Endpoints:
  - `GET /health`
  - `POST /redaccion/draft`
  - `POST /image2json/parse`

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=./src uvicorn app:app --reload
```
