# app.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mininode_api.api.auth_check import router as auth_router

app = FastAPI(title="Mininode API", version="0.1.0")

# Lee origins coma-separados desde env
raw = os.getenv("FRONTEND_ORIGINS", "*")
origins = [o.strip() for o in raw.split(",")] if raw != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,                 # p.ej. ["https://mininode.io", "https://www.mininode.io"]
    allow_credentials=False,               # déjalo en False si no usas cookies/sesiones
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Api-Key"],
    expose_headers=["*"],
    max_age=600,
)

app.include_router(auth_router, prefix="", tags=["auth"])

