import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from mininode_api.api.health import router as health_router
from mininode_api.api.redaccion import router as redaccion_router
from mininode_api.api.image2json import router as image2json_router
from mininode_api.core.auth import require_api_key

app = FastAPI(title="Mininode API", version="0.1.0")

# CORS
raw = os.getenv("FRONTEND_ORIGINS", "*")
origins = [o.strip() for o in raw.split(",")] if raw != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Api-Key"],
    expose_headers=["*"],
    max_age=600,
)

# Routers
app.include_router(health_router, prefix="", tags=["health"])
app.include_router(redaccion_router, prefix="/redaccion", tags=["redaccion"])
app.include_router(image2json_router, prefix="/image2json", tags=["image2json"])

# /auth/check inline para evitar problemas de import
@app.get("/auth/check", tags=["auth"], dependencies=[Depends(require_api_key)])
def auth_check():
    return {"ok": True}
