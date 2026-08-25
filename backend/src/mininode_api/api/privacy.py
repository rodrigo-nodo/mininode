"""HTTP endpoint for Privacy Diagnostic API v0.1."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from mininode_api.core.auth import require_api_key
from mininode_api.services.privacy_diagnostic import PrivacyInspectionError, diagnose_privacy_url
from mininode_api.services import privacy_correction_plan

router = APIRouter(prefix="/privacy", tags=["Privacy"])
logger = logging.getLogger(__name__)


class PrivacyDiagnosticRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


class CorrectionPlanSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: str = Field(min_length=1)
    actions_version: str = Field(min_length=1)
    initial_score: int = Field(ge=0, le=100)
    item_count: int = Field(ge=0)
    items: list[Any]


class CreateCorrectionPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_url: str = Field(min_length=1)
    plan: CorrectionPlanSnapshot


class CreateCorrectionPlanResponse(BaseModel):
    access_token: str
    plan_path: str


class StoredCorrectionPlanResponse(BaseModel):
    id: UUID
    site_url: str
    created_at: datetime
    plan: dict[str, Any]


def _require_correction_plan_database(request: Request) -> None:
    if not request.app.state.privacy_correction_plan_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de planes no disponible.",
        )


@router.post(
    "/correction-plans",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateCorrectionPlanResponse,
    dependencies=[Depends(require_api_key), Depends(_require_correction_plan_database)],
)
def create_correction_plan(request: CreateCorrectionPlanRequest):
    created = privacy_correction_plan.create_correction_plan(
        site_url=request.site_url,
        plan=request.plan.model_dump(),
    )
    return {
        "access_token": created.access_token,
        "plan_path": f"/privacy/plan/{created.access_token}",
    }


@router.get(
    "/correction-plans/{access_token}",
    response_model=StoredCorrectionPlanResponse,
    dependencies=[Depends(_require_correction_plan_database)],
)
def get_correction_plan(access_token: str):
    try:
        return privacy_correction_plan.get_correction_plan(access_token)
    except privacy_correction_plan.CorrectionPlanNotFoundError:
        raise HTTPException(status_code=404, detail="Plan no encontrado.") from None


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
def diagnose_privacy(
    request: PrivacyDiagnosticRequest,
    x_mininode_diagnostics: str | None = Header(default=None, alias="X-Mininode-Diagnostics"),
):
    try:
        return diagnose_privacy_url(request.url)
    except PrivacyInspectionError as exc:
        status_code, message = _ERRORS[exc.code]
        content = {"error": exc.code, "message": message}
        if x_mininode_diagnostics == "1" and exc.diagnostic is not None:
            content["diagnostic"] = exc.diagnostic
        return JSONResponse(status_code=status_code, content=content)
    except Exception:
        logger.exception("Unexpected Privacy Diagnostic failure")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "No fue posible completar el diagnóstico."},
        )
