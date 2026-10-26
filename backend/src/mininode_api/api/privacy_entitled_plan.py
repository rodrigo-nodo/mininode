"""Authenticated Privacy Web plan endpoints backed by active entitlements."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from mininode_api.core.access_auth import require_access_user
from mininode_api.services import access, privacy_entitled_plan

router = APIRouter(prefix="/privacy/workspace-sites", tags=["Privacy Web"])


def _ready(request: Request):
    if not (request.app.state.privacy_entitled_plan_ready
            and request.app.state.privacy_diagnostic_snapshot_ready
            and request.app.state.access_ready):
        raise HTTPException(status_code=503, detail="Privacy Web no disponible temporalmente.")


def _problem(exc: Exception):
    if isinstance(exc, privacy_entitled_plan.PlanUnavailable):
        raise HTTPException(status_code=403, detail="Privacy Web no está activo para este sitio.") from None
    if isinstance(exc, privacy_entitled_plan.PlanNotFound):
        raise HTTPException(status_code=409, detail="No hay un diagnóstico disponible para este sitio.") from None
    if isinstance(exc, privacy_entitled_plan.CheckUnavailable):
        raise HTTPException(status_code=503, detail="No pudimos completar la revisión. Intenta nuevamente.") from None
    raise exc


@router.post("/{workspace_site_id}/plan", dependencies=[Depends(_ready)])
def ensure_plan(workspace_site_id: UUID, user: access.StoredUser = Depends(require_access_user)):
    try:
        return privacy_entitled_plan.ensure_plan(user.id, workspace_site_id)
    except (privacy_entitled_plan.PlanUnavailable, privacy_entitled_plan.PlanNotFound) as exc:
        _problem(exc)


@router.get("/{workspace_site_id}/plan", dependencies=[Depends(_ready)])
def get_plan(workspace_site_id: UUID, user: access.StoredUser = Depends(require_access_user)):
    try:
        return privacy_entitled_plan.get_plan(user.id, workspace_site_id)
    except (privacy_entitled_plan.PlanUnavailable, privacy_entitled_plan.PlanNotFound) as exc:
        _problem(exc)


@router.post("/{workspace_site_id}/plan/check", dependencies=[Depends(_ready)])
def review_plan(workspace_site_id: UUID, user: access.StoredUser = Depends(require_access_user)):
    try:
        return privacy_entitled_plan.review(user.id, workspace_site_id)
    except (privacy_entitled_plan.PlanUnavailable, privacy_entitled_plan.PlanNotFound,
            privacy_entitled_plan.CheckUnavailable) as exc:
        _problem(exc)
