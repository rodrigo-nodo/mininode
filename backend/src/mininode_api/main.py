# -*- coding: utf-8 -*-
# backend/src/mininode_api/main.py
from __future__ import annotations
import os
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Header, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    from mininode_api.services import learn_feedback, privacy_correction_plan

    try:
        learn_feedback.initialize_database()
    except Exception:
        logging.getLogger(__name__).exception(
            "Learn feedback database initialization failed; feedback remains unavailable"
        )
    else:
        app.state.learn_feedback_ready = True

    try:
        privacy_correction_plan.initialize_database()
    except Exception:
        logging.getLogger(__name__).exception(
            "Privacy correction plan database initialization failed; plans remain unavailable"
        )
    else:
        app.state.privacy_correction_plan_ready = True
    yield


def configure_application_logging() -> None:
    """Expose Mininode INFO logs through Uvicorn's existing error handlers."""

    application_logger = logging.getLogger("mininode_api")
    application_logger.setLevel(logging.INFO)

    uvicorn_logger: logging.Logger | None = logging.getLogger("uvicorn.error")
    while uvicorn_logger is not None and not uvicorn_logger.handlers:
        uvicorn_logger = uvicorn_logger.parent
    uvicorn_handlers = uvicorn_logger.handlers if uvicorn_logger is not None else []
    if not uvicorn_handlers:
        # Outside Uvicorn (notably tests), let the surrounding process capture
        # records rather than creating and owning a new handler here.
        application_logger.propagate = True
        return

    for handler in uvicorn_handlers:
        if handler not in application_logger.handlers:
            application_logger.addHandler(handler)
    application_logger.propagate = False


# Patrón app factory: facilita tests, evita efectos colaterales al importar.
def create_app() -> FastAPI:
    app = FastAPI(title="Mininode API", version="0.1.0", lifespan=lifespan)
    app.state.learn_feedback_ready = False
    app.state.privacy_correction_plan_ready = False

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

    # Endpoints básicos
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.head("/")
    async def root_head():
        return Response(status_code=204)

    @app.get("/")
    async def root_get():
        return {"status": "ok"}

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return RedirectResponse(
            url=os.getenv("PUBLIC_FAVICON_URL", "https://mininode.io/favicon.ico")
        )

    # Routers existentes (se incluyen si están disponibles)
    try:
        from mininode_api.api.auth_check import router as auth_router
        app.include_router(auth_router)
    except Exception as e:
        logging.exception("Failed to include auth_check router: %s", e)

    try:
        from mininode_api.api.write import router as write_router
        app.include_router(write_router)
    except Exception as e:
        logging.exception("Failed to include write router: %s", e)

    try:
        from mininode_api.api.capture import router as capture_router
        app.include_router(capture_router)
    except Exception as e:
        logging.exception("Failed to include capture router: %s", e)

    # Routers nuevos (upload + orquestador de pipelines)
    try:
        from mininode_api.api.files import router as files_router
        app.include_router(files_router)
    except Exception as e:
        logging.exception("Failed to include files router: %s", e)

    try:
        from mininode_api.api.imaging import router as imaging_router   # ← NUEVO
        app.include_router(imaging_router)
    except Exception as e:
        logging.exception("Failed to include imaging router: %s", e)
        
    try:
        from mininode_api.api.pipeline_orchestrator import router as pipeline_router
        app.include_router(pipeline_router)
    except Exception as e:
        logging.exception("Failed to include pipeline_orchestrator router: %s", e)

    try:
        from mininode_api.api.privacy import router as privacy_router
        app.include_router(privacy_router)
    except Exception as e:
        logging.exception("Failed to include privacy router: %s", e)

    from mininode_api.api.learn import router as learn_router
    app.include_router(learn_router)

    # Analyze: intenta incluir router; si no existe, define fallback /analyze/summary
    analyze_router_included = False
    try:
        from mininode_api.api.analyze import router as analyze_router
        app.include_router(analyze_router)
        analyze_router_included = True
    except Exception as e:
        logging.exception("Failed to include analyze router: %s", e)

    if not analyze_router_included:
        # Modelos y servicio reales
        try:
            from mininode_api.models.analyze import SummaryIn, SummaryOut
            from mininode_api.core.analyze_service import analyze_summary_service
        except Exception as e:
            logging.exception("Analyze fallback unavailable: %s", e)
            SummaryIn = SummaryOut = None
            analyze_summary_service = None  # type: ignore

        MININODE_API_KEY = os.getenv("MININODE_API_KEY", "")

        async def require_api_key(x_api_key: str = Header(default="")):
            # Guardia mínima; si no hay clave configurada, permite paso (útil en dev).
            if MININODE_API_KEY and x_api_key != MININODE_API_KEY:
                raise HTTPException(status_code=401, detail="Invalid X-Api-Key")
            return True

        if SummaryIn and SummaryOut and analyze_summary_service:
            @app.post("/analyze/summary", response_model=SummaryOut, dependencies=[Depends(require_api_key)])
            async def analyze_summary(body: SummaryIn) -> SummaryOut:  # type: ignore[valid-type]
                return await analyze_summary_service(body)  # type: ignore[misc]

    return app


# Punto de entrada para Uvicorn/Render
configure_application_logging()
app = create_app()
