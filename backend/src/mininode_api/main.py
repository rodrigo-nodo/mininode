# -*- coding: utf-8 -*-
# backend/src/mininode_api/main.py
from __future__ import annotations
import os
from typing import List
from fastapi import FastAPI, Header, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mininode API", version="0.1.0")

# CORS desde env (coma-separado)
origins_env = os.getenv("ALLOWED_ORIGINS", "https://mininode.io,https://*.pages.dev")
allowed_origins: List[str] = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

# Raíz: evita 404 en probes HEAD /
@app.head("/")
async def root_head():
    return Response(status_code=204)

@app.get("/")
async def root_get():
    return {"status": "ok"}

# Intenta incluir routers existentes (si los tienes ya)
try:
    from mininode_api.api.auth_check import router as auth_router
    app.include_router(auth_router)
except Exception:
    pass

try:
    from mininode_api.api.write import router as write_router
    app.include_router(write_router)
except Exception:
    pass

try:
    from mininode_api.api.capture import router as capture_router
    app.include_router(capture_router)
except Exception:
    pass

analyze_router_included = False
try:
    from mininode_api.api.analyze import router as analyze_router
    app.include_router(analyze_router)
    analyze_router_included = True
except Exception:
    analyze_router_included = False

# Fallback de /analyze/summary si no existe router
if not analyze_router_included:
    # Importa solo los modelos desde models
    from mininode_api.models.analyze import (
        SummaryIn, SummaryOut
    )
    # Y la lógica de servicio real desde core (o services)
    from mininode_api.core.analyze_service import analyze_summary_service

    MININODE_API_KEY = os.getenv("MININODE_API_KEY", "")

    async def require_api_key(x_api_key: str = Header(default="")):
        # Guardia mínima para mantener contrato. Si no hay clave configurada, permite paso.
        if MININODE_API_KEY and x_api_key != MININODE_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid X-Api-Key")
        return True

    @app.post("/analyze/summary", response_model=SummaryOut, dependencies=[Depends(require_api_key)])
    async def analyze_summary(body: SummaryIn) -> SummaryOut:
        return await analyze_summary_service(body)
