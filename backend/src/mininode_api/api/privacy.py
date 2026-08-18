"""HTTP endpoint for Privacy Diagnostic API v0.1."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from mininode_api.core.auth import require_api_key
from mininode_api.services.privacy_diagnostic import PrivacyInspectionError, diagnose_privacy_url

router = APIRouter(prefix="/privacy", tags=["Privacy"])
logger = logging.getLogger(__name__)


class PrivacyDiagnosticRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


_ERRORS = {
    "invalid_url": (400, "La URL debe usar HTTP o HTTPS y contener un hostname válido."),
    "unsafe_target": (400, "El destino solicitado no es seguro para inspección."),
    "inspection_blocked": (422, "El sitio no permite inspeccionar la página inicial."),
    "dns_resolution_failed": (422, "No fue posible resolver el hostname solicitado."),
    "request_timeout": (422, "El sitio no respondió dentro del tiempo permitido."),
    "tls_failure": (422, "No fue posible verificar la conexión segura del sitio."),
    "http_fetch_failed": (422, "No fue posible obtener la página inicial del sitio."),
    "unsupported_content_type": (422, "La página inicial no contiene un formato compatible."),
    "inspection_failed": (422, "No fue posible inspeccionar el sitio solicitado."),
}


@router.post("/diagnose", dependencies=[Depends(require_api_key)])
def diagnose_privacy(request: PrivacyDiagnosticRequest):
    try:
        return diagnose_privacy_url(request.url)
    except PrivacyInspectionError as exc:
        status_code, message = _ERRORS[exc.code]
        return JSONResponse(status_code=status_code, content={"error": exc.code, "message": message})
    except Exception:
        logger.exception("Unexpected Privacy Diagnostic failure")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "No fue posible completar el diagnóstico."},
        )
