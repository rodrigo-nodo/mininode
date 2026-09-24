"""HTTP endpoint for Privacy Diagnostic API v0.1."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mininode_api.core.auth import require_api_key
from mininode_api.services.privacy_diagnostic import PrivacyInspectionError, diagnose_privacy_url
from mininode_api.services import privacy_correction_plan
from mininode_api.services import privacy_correction_plan_flow
from mininode_api.services import privacy_correction_plan_activation
from mininode_api.services import privacy_correction_plan_order
from mininode_api.services import privacy_correction_plan_check
from mininode_api.services import privacy_diagnostic_snapshot

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


class CreateCorrectionPlanFromUrlResponse(CreateCorrectionPlanResponse):
    initial_score: int
    item_count: int


class StoredCorrectionPlanResponse(BaseModel):
    id: UUID
    site_url: str
    created_at: datetime
    plan: dict[str, Any]
    check: dict[str, Any] | None = None


class CreateCorrectionPlanOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnostic_id: UUID
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local, separator, domain = normalized.rpartition("@")
        if (
            not separator
            or normalized.count("@") != 1
            or not local
            or not domain
            or "." not in domain
            or any(character.isspace() for character in normalized)
        ):
            raise ValueError("email inválido")
        return normalized


class CreateCorrectionPlanOrderResponse(BaseModel):
    order_id: UUID
    product: str
    amount: int
    currency: str
    status: str


class CorrectionPlanOrderResponse(BaseModel):
    id: UUID
    diagnostic_id: UUID
    correction_plan_id: UUID | None
    site_url: str
    email: str
    product_code: str
    amount: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None


class ActivateCorrectionPlanOrderResponse(BaseModel):
    order_id: UUID
    status: str
    correction_plan_id: UUID
    plan_path: str


def _require_correction_plan_database(request: Request) -> None:
    if not request.app.state.privacy_correction_plan_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de Privacy Web no disponible.",
        )


def _require_correction_plan_order_database(request: Request) -> None:
    if (
        not request.app.state.privacy_correction_plan_order_ready
        or not request.app.state.privacy_diagnostic_snapshot_ready
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de órdenes no disponible.",
        )


def _require_correction_plan_check_database(request: Request) -> None:
    if not request.app.state.privacy_correction_plan_check_ready:
        raise HTTPException(status_code=503, detail="Servicio de revisión no disponible.")


@router.post(
    "/correction-plan-orders",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateCorrectionPlanOrderResponse,
    dependencies=[Depends(_require_correction_plan_order_database)],
)
def create_correction_plan_order(request: CreateCorrectionPlanOrderRequest):
    try:
        order = privacy_correction_plan_order.create_order(
            diagnostic_id=request.diagnostic_id, email=request.email
        )
    except privacy_diagnostic_snapshot.PrivacyDiagnosticSnapshotNotFoundError:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado.") from None
    except privacy_diagnostic_snapshot.PrivacyDiagnosticPurchaseExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "El diagnóstico ya no está disponible para activar Privacy Web. "
                "Realice una nueva revisión."
            ),
        ) from None
    except Exception:
        # Do not attach exception details: database errors must never leak the email.
        logger.error("Privacy correction plan order creation failed")
        raise HTTPException(status_code=503, detail="Servicio de órdenes no disponible.") from None
    return {
        "order_id": order.id,
        "product": order.product_code,
        "amount": order.amount,
        "currency": order.currency,
        "status": order.status,
    }


@router.get(
    "/correction-plan-orders/{order_id}",
    response_model=CorrectionPlanOrderResponse,
    dependencies=[Depends(require_api_key), Depends(_require_correction_plan_order_database)],
)
def get_correction_plan_order(order_id: UUID):
    try:
        return privacy_correction_plan_order.get_order(order_id)
    except privacy_correction_plan_order.CorrectionPlanOrderNotFoundError:
        raise HTTPException(status_code=404, detail="Orden no encontrada.") from None


@router.post(
    "/correction-plan-orders/{order_id}/mark-paid",
    response_model=CorrectionPlanOrderResponse,
    dependencies=[Depends(require_api_key), Depends(_require_correction_plan_order_database)],
)
def mark_correction_plan_order_paid(order_id: UUID):
    try:
        return privacy_correction_plan_order.mark_order_paid(order_id)
    except privacy_correction_plan_order.CorrectionPlanOrderNotFoundError:
        raise HTTPException(status_code=404, detail="Orden no encontrada.") from None


@router.post(
    "/correction-plan-orders/{order_id}/activate",
    response_model=ActivateCorrectionPlanOrderResponse,
    dependencies=[
        Depends(require_api_key),
        Depends(_require_correction_plan_database),
        Depends(_require_correction_plan_order_database),
    ],
)
def activate_correction_plan_order(order_id: UUID):
    try:
        return privacy_correction_plan_activation.activate_order(order_id)
    except privacy_correction_plan_order.CorrectionPlanOrderNotFoundError:
        raise HTTPException(status_code=404, detail="Orden no encontrada.") from None
    except privacy_correction_plan_activation.OrderAlreadyActivatedError:
        raise HTTPException(status_code=409, detail="La orden ya fue activada.") from None
    except privacy_correction_plan_activation.OrderActivationStateError:
        raise HTTPException(
            status_code=409, detail="La orden no se encuentra en un estado activable."
        ) from None


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


@router.post(
    "/correction-plans/from-url",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateCorrectionPlanFromUrlResponse,
    dependencies=[Depends(require_api_key), Depends(_require_correction_plan_database)],
)
def create_correction_plan_from_url(request: PrivacyDiagnosticRequest):
    try:
        created, plan = privacy_correction_plan_flow.create_correction_plan_from_url(
            request.url
        )
    except PrivacyInspectionError as exc:
        status_code, message = _ERRORS[exc.code]
        return JSONResponse(
            status_code=status_code,
            content={"error": exc.code, "message": message},
        )
    except privacy_correction_plan_flow.NoActionableItemsError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "no_actionable_items", "message": str(exc)},
        )
    return {
        "access_token": created.access_token,
        "plan_path": f"/privacy/plan/{created.access_token}",
        "initial_score": plan["initial_score"],
        "item_count": plan["item_count"],
    }


@router.get(
    "/correction-plans/{access_token}",
    response_model=StoredCorrectionPlanResponse,
    dependencies=[Depends(_require_correction_plan_database)],
)
def get_correction_plan(access_token: str, request: Request):
    try:
        plan = privacy_correction_plan.get_correction_plan(access_token)
        check = (
            privacy_correction_plan_check.get_check_metadata(plan["id"])
            if request.app.state.privacy_correction_plan_check_ready
            else None
        )
        return {**plan, "check": check}
    except privacy_correction_plan.CorrectionPlanNotFoundError:
        raise HTTPException(status_code=404, detail="Privacy Web no disponible.") from None
    except privacy_correction_plan_check.ImprovementCheckNotFoundError:
        raise HTTPException(status_code=404, detail="Privacy Web no disponible.") from None


@router.post(
    "/correction-plans/{access_token}/check",
    dependencies=[Depends(_require_correction_plan_database), Depends(_require_correction_plan_check_database)],
)
def check_correction_plan(access_token: str):
    try:
        return privacy_correction_plan_check.perform_check(access_token)
    except privacy_correction_plan_check.ImprovementCheckNotFoundError:
        raise HTTPException(status_code=404, detail="Privacy Web no disponible.") from None
    except privacy_correction_plan_check.ImprovementCheckExpiredError:
        raise HTTPException(status_code=410, detail="La vigencia de Privacy Web ha finalizado.") from None
    except privacy_correction_plan_check.ImprovementCheckUnavailableError:
        raise HTTPException(status_code=409, detail="La revisión de Privacy Web no está disponible.") from None
    except privacy_correction_plan_check.ImprovementInspectionError:
        raise HTTPException(status_code=503, detail="No pudimos completar la revisión. Intente nuevamente en unos minutos.") from None


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
    body: PrivacyDiagnosticRequest,
    request: Request,
    x_mininode_diagnostics: str | None = Header(default=None, alias="X-Mininode-Diagnostics"),
):
    try:
        diagnostic = diagnose_privacy_url(body.url)
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

    if request.app.state.privacy_diagnostic_snapshot_ready:
        try:
            stored = privacy_diagnostic_snapshot.create_diagnostic_snapshot(diagnostic)
        except Exception:
            # The free result remains available when the commercial persistence fails.
            logger.error("Privacy diagnostic snapshot persistence failed")
        else:
            diagnostic = {
                **diagnostic,
                "diagnostic_id": stored.id,
                "purchase_expires_at": stored.purchase_expires_at,
            }
    return diagnostic
