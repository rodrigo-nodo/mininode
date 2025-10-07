import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mininode_api.api.health import router as health_router
from mininode_api.api.write import router as write_router
from mininode_api.api.redaccion import router as redaccion_router  # legacy compat
from mininode_api.api.image2json import router as image2json_router
from mininode_api.api.analyze import router as analyze_router

app = FastAPI(title="Mininode API", version="0.2.0")

raw = os.getenv("FRONTEND_ORIGINS", "*")
origins = [o.strip() for o in raw.split(",")] if raw != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(write_router)
app.include_router(redaccion_router)   # compat temporal
app.include_router(image2json_router)
app.include_router(analyze_router)
