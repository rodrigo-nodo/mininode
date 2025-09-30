from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mininode_api.api.health import router as health_router
from mininode_api.api.redaccion import router as redaccion_router
from mininode_api.api.image2json import router as image2json_router

app = FastAPI(title="Mininode API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(health_router, prefix="", tags=["health"])
app.include_router(redaccion_router, prefix="/redaccion", tags=["redaccion"])
app.include_router(image2json_router, prefix="/image2json", tags=["image2json"])
