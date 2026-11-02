"""HTTP endpoint for Privacy Diagnostic API v0.1."""

from __future__ import annotations

from datetime import datetime, timezone
import secrets
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from mininode_api.core.auth import require_api_key
from mininode_api.core.access_auth import require_access_user
from mininode_api.services import access
from mininode_api.services.privacy_diagnostic import PrivacyInspectionError, diagnose_privacy_url
from mininode_api.services import privacy_diagnostic_snapshot

router = APIRouter(prefix="/privacy", tags=["Privacy"])
logger = logging.getLogger(__name__)


class PrivacyDiagnosticRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


class ClaimAnonymousDiagnosticRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    diagnostic_id: UUID
    workspace_id: UUID
    claim_token: str = Field(min_length=32, max_length=512)


class ClaimedDiagnosticResponse(BaseModel):
    diagnostic_id: UUID
    workspace_site_id: UUID


def _require_privacy_snapshot_database(request: Request) -> None:
    if not request.app.state.privacy_diagnostic_snapshot_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de revisiones no disponible.",
        )


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


def _review_summary(stored: privacy_diagnostic_snapshot.StoredPrivacyDiagnostic) -> dict[str, Any]:
    status_value = stored.diagnostic_snapshot.get("status")
    return {
        "workspace_site_id": stored.workspace_site_id,
        "diagnostic_id": stored.id,
        "score": stored.score,
        "status": status_value if isinstance(status_value, str) else None,
        "created_at": stored.created_at,
    }


@router.get(
    "/workspace-sites/{workspace_site_id}/latest-review",
    dependencies=[Depends(_require_privacy_snapshot_database)],
)
def get_latest_workspace_site_review(
    workspace_site_id: UUID,
    user: access.StoredUser = Depends(require_access_user),
):
    if access.get_authorized_site(user.id, workspace_site_id) is None:
        raise HTTPException(status_code=404, detail="Sitio no encontrado.")
    try:
        stored = privacy_diagnostic_snapshot.get_latest_for_workspace_site(workspace_site_id)
    except privacy_diagnostic_snapshot.PrivacyDiagnosticSnapshotNotFoundError:
        raise HTTPException(status_code=404, detail="Revisión no encontrada.") from None

    return {
        **stored.diagnostic_snapshot,
        "diagnostic_id": stored.id,
        "created_at": stored.created_at,
        "purchase_expires_at": stored.purchase_expires_at,
        "workspace_site_id": stored.workspace_site_id,
    }


@router.post(
    "/workspace-sites/{workspace_site_id}/prepare-activation",
    dependencies=[Depends(_require_privacy_snapshot_database)],
)
def prepare_workspace_site_activation(
    workspace_site_id: UUID,
    request: Request,
    user: access.StoredUser = Depends(require_access_user),
):
    """Re-use a recent saved diagnosis; safely refresh an older one before checkout.

    This preparation does not create orders, entitlements or payments.
    The original saved diagnosis is retained even when a refresh fails.
    """
    if access.get_authorized_site(user.id, workspace_site_id) is None:
        raise HTTPException(status_code=404, detail="Sitio no encontrado.")
    try:
        latest = privacy_diagnostic_snapshot.get_latest_for_workspace_site(workspace_site_id)
    except privacy_diagnostic_snapshot.PrivacyDiagnosticSnapshotNotFoundError:
        raise HTTPException(status_code=409, detail="Realiza un diagnóstico antes de activar Privacy Web.") from None

    if latest.purchase_expires_at > datetime.now(timezone.utc):
        return {
            "refreshed": False,
            "diagnostic": {
                **latest.diagnostic_snapshot,
                "diagnostic_id": latest.id,
                "created_at": latest.created_at,
                "purchase_expires_at": latest.purchase_expires_at,
                "workspace_site_id": workspace_site_id,
            },
        }

    # Re-use the same authenticated inspector and stored URL as manual reviews.
    # Never let an unsaved inspection proceed to checkout as a recent diagnosis.
    refreshed = diagnose_workspace_site(workspace_site_id, request, user)
    if isinstance(refreshed, JSONResponse):
        return refreshed
    if not refreshed.get("diagnostic_id") or not refreshed.get("purchase_expires_at"):
        raise HTTPException(
            status_code=503,
            detail="No pudimos guardar la nueva revisión. Intenta nuevamente.",
        )
    return {
        "refreshed": True,
        "diagnostic": {**refreshed, "workspace_site_id": workspace_site_id},
    }


@router.get(
    "/workspaces/{workspace_id}/latest-reviews",
    dependencies=[Depends(_require_privacy_snapshot_database)],
)
def list_workspace_latest_reviews(
    workspace_id: UUID,
    user: access.StoredUser = Depends(require_access_user),
):
    try:
        workspaces = access.list_authorized_context(user.id)
    except Exception:
        logger.exception("Access workspace lookup failed before Privacy review listing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        ) from None

    if not any(workspace.id == workspace_id for workspace in workspaces):
        raise HTTPException(status_code=404, detail="Espacio no encontrado.")

    try:
        reviews = privacy_diagnostic_snapshot.list_latest_for_workspace(workspace_id)
    except Exception:
        logger.exception("Privacy review listing failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No pudimos cargar tus revisiones.",
        ) from None
    return {"reviews": [_review_summary(review) for review in reviews]}


@router.post("/workspace-sites/{workspace_site_id}/diagnose")
def diagnose_workspace_site(
    workspace_site_id: UUID,
    request: Request,
    user: access.StoredUser = Depends(require_access_user),
):
    authorized = access.get_authorized_site(user.id, workspace_site_id)
    if authorized is None:
        raise HTTPException(status_code=404, detail="Sitio no encontrado.")
    if not authorized.hostname:
        raise HTTPException(status_code=409, detail="Sitio no disponible para diagnóstico.")
    target_url = authorized.canonical_url or f"https://{authorized.hostname}"
    try:
        diagnostic = diagnose_privacy_url(target_url)
    except PrivacyInspectionError as exc:
        status_code, message = _ERRORS[exc.code]
        return JSONResponse(status_code=status_code, content={"error": exc.code, "message": message})
    except Exception:
        logger.exception("Unexpected authenticated Privacy Diagnostic failure")
        return JSONResponse(status_code=500, content={"error": "internal_error", "message": "No fue posible completar el diagnóstico."})

    if request.app.state.privacy_diagnostic_snapshot_ready:
        try:
            stored = privacy_diagnostic_snapshot.create_diagnostic_snapshot(
                diagnostic, workspace_site_id=workspace_site_id, requested_url=target_url
            )
        except Exception:
            logger.error("Authenticated Privacy diagnostic snapshot persistence failed")
        else:
            diagnostic = {**diagnostic, "diagnostic_id": stored.id, "purchase_expires_at": stored.purchase_expires_at}
    return diagnostic


@router.post("/workspaces/{workspace_id}/diagnose")
def diagnose_workspace_url(
    workspace_id: UUID,
    body: PrivacyDiagnosticRequest,
    request: Request,
    user: access.StoredUser = Depends(require_access_user),
):
    """Diagnose a URL and associate the successful review with an authorized workspace."""

    try:
        workspaces = access.list_authorized_context(user.id)
    except Exception:
        logger.exception("Access workspace lookup failed before Privacy diagnosis")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        ) from None

    if not any(workspace.id == workspace_id for workspace in workspaces):
        raise HTTPException(status_code=404, detail="Espacio no encontrado.")

    try:
        # Access owns the canonical Site rules. Validate those rules before spending
        # inspection work, but do not persist the Site until the diagnosis succeeds.
        access.normalize_site_url(body.url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None

    try:
        diagnostic = diagnose_privacy_url(body.url)
    except PrivacyInspectionError as exc:
        status_code, message = _ERRORS[exc.code]
        return JSONResponse(
            status_code=status_code,
            content={"error": exc.code, "message": message},
        )
    except Exception:
        logger.exception("Unexpected workspace Privacy Diagnostic failure")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "No fue posible completar el diagnóstico."},
        )

    try:
        # Associate by inspected HOME, exactly as anonymous diagnostic claims do.
        # Keep the user-entered origin independently in requested_url below.
        site = access.follow_site(user.id, workspace_id, diagnostic["site_url"])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
    except Exception:
        logger.exception("Automatic Privacy site association failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No pudimos guardar el sitio en tu cuenta.",
        ) from None

    if site is None:
        raise HTTPException(status_code=404, detail="Espacio no encontrado.")

    if request.app.state.privacy_diagnostic_snapshot_ready:
        try:
            stored = privacy_diagnostic_snapshot.create_diagnostic_snapshot(
                diagnostic, workspace_site_id=site.id, requested_url=body.url
            )
        except Exception:
            logger.error("Workspace Privacy diagnostic snapshot persistence failed")
        else:
            diagnostic = {
                **diagnostic,
                "diagnostic_id": stored.id,
                "purchase_expires_at": stored.purchase_expires_at,
            }
    return {**diagnostic, "workspace_site_id": site.id}


@router.post(
    "/diagnostic-claims",
    response_model=ClaimedDiagnosticResponse,
    dependencies=[Depends(_require_privacy_snapshot_database)],
)
def claim_diagnostic(body: ClaimAnonymousDiagnosticRequest, user: access.StoredUser = Depends(require_access_user)):
    try:
        site_id = privacy_diagnostic_snapshot.claim_anonymous_diagnostic(
            body.diagnostic_id, body.claim_token, user.id, body.workspace_id
        )
    except privacy_diagnostic_snapshot.PrivacyDiagnosticClaimRejectedError:
        raise HTTPException(status_code=409, detail="No se pudo asociar este diagnóstico.") from None
    except ValueError:
        raise HTTPException(status_code=422, detail="No se pudo asociar este diagnóstico.") from None
    return ClaimedDiagnosticResponse(diagnostic_id=body.diagnostic_id, workspace_site_id=site_id)


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
            claim_token = secrets.token_urlsafe(32)
            stored = privacy_diagnostic_snapshot.create_diagnostic_snapshot(
                diagnostic, claim_token=claim_token, requested_url=body.url
            )
        except Exception:
            # The free result remains available when the commercial persistence fails.
            logger.error("Privacy diagnostic snapshot persistence failed")
        else:
            diagnostic = {
                **diagnostic,
                "diagnostic_id": stored.id,
                "purchase_expires_at": stored.purchase_expires_at,
                "claim_token": claim_token,
            }
    return diagnostic
