# -*- coding: utf-8 -*-
# backend/src/mininode_api/main.py
from __future__ import annotations
import os
from typing import List
from fastapi import FastAPI, Header, HTTPException, Depends
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

# Intenta incluir routers existentes (si los tienes ya)
try:
    from mininode_api.api.routers.auth import router as auth_router
    app.include_router(auth_router)
except Exception:
    pass

try:
    from mininode_api.api.routers.redaccion import router as redaccion_router
    app.include_router(redaccion_router)
except Exception:
    pass

analisis_router_included = False
try:
    from mininode_api.api.routers.analisis import router as analisis_router
    app.include_router(analisis_router)
    analisis_router_included = True
except Exception:
    analisis_router_included = False

# Fallback de /analisis/summary si no existe router
if not analisis_router_included:
    from mininode_api.core.models.analyze import (
        SummaryIn, SummaryOut, analisis_summary_service
    )

    MININODE_API_KEY = os.getenv("MININODE_API_KEY", "")

    async def require_api_key(x_api_key: str = Header(default="")):
        # Guardia mínima para mantener contrato. Si no hay clave configurada, permite paso.
        if MININODE_API_KEY and x_api_key != MININODE_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid X-Api-Key")
        return True

    @app.post("/analisis/summary", response_model=SummaryOut, dependencies=[Depends(require_api_key)])
    async def analisis_summary(body: SummaryIn) -> SummaryOut:
        return await analisis_summary_service(body)
