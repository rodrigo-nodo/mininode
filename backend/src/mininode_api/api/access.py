"""Mininode Access identity and authorization endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from mininode_api.core.access_auth import require_access_user
from mininode_api.services import access, site_group_reviews, site_group_operator, admin_grants

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/access", tags=["access"])


class AccessMeResponse(BaseModel):
    user_id: UUID
    email: str


class AccessSiteContextResponse(BaseModel):
    id: UUID
    site_id: UUID
    hostname: str
    company_id: UUID | None
    company_name: str | None


class AccessWorkspaceContextResponse(BaseModel):
    id: UUID
    name: str
    role: str
    sites: list[AccessSiteContextResponse]


class AccessContextResponse(BaseModel):
    workspaces: list[AccessWorkspaceContextResponse]


class AccessFollowSiteRequest(BaseModel):
    url: str


class AccessFollowSiteResponse(BaseModel):
    id: UUID
    site_id: UUID
    hostname: str


class SiteGroupReviewRequest(BaseModel):
    first_workspace_site_id: UUID
    second_workspace_site_id: UUID


class SiteGroupReviewResponse(BaseModel):
    id: UUID
    first_workspace_site_id: UUID
    second_workspace_site_id: UUID
    status: str


class SiteGroupReviewListResponse(BaseModel):
    reviews: list[SiteGroupReviewResponse]


class SiteGroupDecisionRequest(BaseModel):
    decision: str
    note: str


class SiteGroupDecisionResponse(BaseModel):
    id: UUID
    status: str
    moved_diagnostics: int


class SiteGroupOperatorListResponse(BaseModel):
    reviews: list[dict]


class AccessOnboardingResponse(BaseModel):
    workspace_id: UUID
    name: str
    role: str


@router.get("/me", response_model=AccessMeResponse)
def access_me(
    user: access.StoredUser = Depends(require_access_user),
) -> AccessMeResponse:
    return AccessMeResponse(user_id=user.id, email=user.email)


@router.post("/onboarding", response_model=AccessOnboardingResponse)
def access_onboarding(
    user: access.StoredUser = Depends(require_access_user),
) -> AccessOnboardingResponse:
    try:
        workspace = access.get_or_create_personal_workspace(user.id)
    except Exception:
        logger.exception("Access onboarding failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        )

    return AccessOnboardingResponse(
        workspace_id=workspace.id,
        name=workspace.name,
        role=workspace.role,
    )


@router.post("/workspaces/{workspace_id}/sites", response_model=AccessFollowSiteResponse)
def access_follow_site(
    workspace_id: UUID,
    request: AccessFollowSiteRequest,
    user: access.StoredUser = Depends(require_access_user),
) -> AccessFollowSiteResponse:
    try:
        site = access.follow_site(user.id, workspace_id, request.url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception:
        logger.exception("Access site association failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return AccessFollowSiteResponse(id=site.id, site_id=site.site_id, hostname=site.hostname)


@router.post(
    "/workspaces/{workspace_id}/site-group-reviews",
    response_model=SiteGroupReviewResponse,
)
def access_request_site_group_review(
    workspace_id: UUID,
    body: SiteGroupReviewRequest,
    user: access.StoredUser = Depends(require_access_user),
):
    try:
        review = site_group_reviews.create_review_request(
            user.id, workspace_id,
            body.first_workspace_site_id, body.second_workspace_site_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except site_group_reviews.ReviewQueueUnavailable:
        raise HTTPException(status_code=503, detail="La revisión de sitios no está disponible.") from None
    except Exception:
        logger.exception("Access site review submission failed")
        raise HTTPException(status_code=503, detail="No pudimos solicitar la revisión.") from None
    if review is None:
        raise HTTPException(status_code=404, detail="Sitios no encontrados en este espacio.")
    # The request is committed independently of external mail delivery.
    # Duplicate submissions do not resend a successful notification.
    try:
        site_group_operator.notify_pending(review.id)
    except Exception:
        # Mail cannot undo an already committed request. Retry on submission.
        logger.warning("Review request persisted; operator email not delivered")
    return SiteGroupReviewResponse(**vars(review))


@router.get(
    "/workspaces/{workspace_id}/site-group-reviews",
    response_model=SiteGroupReviewListResponse,
)
def access_list_site_group_reviews(
    workspace_id: UUID,
    user: access.StoredUser = Depends(require_access_user),
):
    try:
        reviews = site_group_reviews.list_review_requests(user.id, workspace_id)
    except site_group_reviews.ReviewQueueUnavailable:
        raise HTTPException(status_code=503, detail="La revisión de sitios no está disponible.") from None
    except Exception:
        logger.exception("Access site review lookup failed")
        raise HTTPException(status_code=503, detail="No pudimos consultar las revisiones.") from None
    if reviews is None:
        raise HTTPException(status_code=404, detail="Espacio no encontrado.")
    return SiteGroupReviewListResponse(
        reviews=[SiteGroupReviewResponse(**vars(item)) for item in reviews],
    )


def _require_review_operator(user: access.StoredUser) -> None:
    if not site_group_operator.is_operator(user.email):
        raise HTTPException(status_code=403, detail="Operador no autorizado.")


@router.get("/operator/site-group-reviews", response_model=SiteGroupOperatorListResponse)
def access_operator_site_group_reviews(
    user: access.StoredUser = Depends(require_access_user),
):
    _require_review_operator(user)
    try:
        return {"reviews": site_group_operator.list_operator_reviews()}
    except Exception:
        logger.exception("Operator review lookup failed")
        raise HTTPException(status_code=503, detail="No pudimos cargar las solicitudes.") from None


@router.post(
    "/operator/site-group-reviews/{review_id}/decision",
    response_model=SiteGroupDecisionResponse,
)
def access_operator_decide_site_group_review(
    review_id: UUID,
    body: SiteGroupDecisionRequest,
    user: access.StoredUser = Depends(require_access_user),
):
    _require_review_operator(user)
    try:
        return site_group_operator.decide(review_id, user.id, body.decision, body.note)
    except LookupError:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.") from None
    except site_group_operator.OperatorConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        logger.exception("Operator review decision failed")
        raise HTTPException(status_code=503, detail="No pudimos resolver la solicitud.") from None


@router.get("/context", response_model=AccessContextResponse)
def access_context(
    user: access.StoredUser = Depends(require_access_user),
) -> AccessContextResponse:
    try:
        workspaces = access.list_authorized_context(user.id)
    except Exception:
        logger.exception("Access authorization context lookup failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        )

    return AccessContextResponse(
        workspaces=[
            AccessWorkspaceContextResponse(
                id=workspace.id,
                name=workspace.name,
                role=workspace.role,
                sites=[
                    AccessSiteContextResponse(
                        id=site.id,
                        site_id=site.site_id,
                        hostname=site.hostname,
                        company_id=site.company_id,
                        company_name=site.company_name,
                    )
                    for site in workspace.sites
                ],
            )
            for workspace in workspaces
        ]
    )


@router.post("/workspaces/{workspace_id}/sites/{workspace_site_id}/unlink", status_code=204)
@router.delete("/workspaces/{workspace_id}/sites/{workspace_site_id}", status_code=204)
def access_unlink_site(
    workspace_id: UUID,
    workspace_site_id: UUID,
    user: access.StoredUser = Depends(require_access_user),
):
    try:
        found = access.unlink_workspace_site(user.id, workspace_id, workspace_site_id)
    except access.ActiveSiteCannotBeUnlinked as exc:
        detail = (
            "Este sitio tiene un servicio activo. Podrá desvincularse cuando finalice su vigencia."
            if exc.reason == "active_entitlement"
            else (
                "Este sitio tiene una compra pendiente. Podrá desvincularse cuando se resuelva."
                if exc.reason == "pending_order"
                else "Este sitio tiene un servicio activo o una compra pendiente y no puede desvincularse."
            )
        )
        raise HTTPException(status_code=409, detail=detail)
    except Exception:
        logger.exception("Access site unlink failed")
        raise HTTPException(status_code=503, detail="El servicio de acceso no está disponible.")
    if not found:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")

class AdminGrantRequest(BaseModel):
    workspace_site_id: UUID
    days: int = 30
    reason: str

class AdminRevokeRequest(BaseModel):
    reason: str

@router.get("/operator/grants/overview")
def operator_grants_overview(user: access.StoredUser = Depends(require_access_user)):
    _require_review_operator(user)
    try:
        totals, rows = admin_grants.list_admin_courtesies()
        return {
            "totals": {"current": totals[0], "scheduled": totals[1], "historical": totals[2]},
            "limit": 100,
            "courtesies": [
                {"id": str(eid), "workspace_site_id": str(sid), "hostname": host,
                 "workspace": workspace, "active_from": start, "active_until": until,
                 "status": status, "last_reason": reason}
                for eid, sid, host, workspace, start, until, status, reason in rows
            ],
        }
    except Exception:
        logger.exception("Admin courtesy overview failed")
        raise HTTPException(status_code=503, detail="No pudimos cargar las cortesías.") from None

@router.get("/operator/grant-sites")
def operator_grant_sites(q: str, user: access.StoredUser = Depends(require_access_user)):
    _require_review_operator(user)
    try:
        return {"sites": [{"id": str(a), "workspace": b, "hostname": c} for a,b,c in admin_grants.search_sites(q)]}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        logger.exception("Admin grant site lookup failed")
        raise HTTPException(status_code=503, detail="No pudimos buscar sitios.") from None

@router.get("/operator/grant-sites/{workspace_site_id}")
def operator_grant_history(workspace_site_id: UUID, user: access.StoredUser = Depends(require_access_user)):
    _require_review_operator(user)
    try:
        rows = admin_grants.list_grants(workspace_site_id)
        return {"entitlements": [{"id": str(a), "active_from": b, "active_until": c, "status": d, "source": e, "last_reason": f} for a,b,c,d,e,f in rows]}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except Exception:
        logger.exception("Admin grant history failed")
        raise HTTPException(status_code=503, detail="No pudimos consultar las vigencias.") from None

@router.post("/operator/grants", status_code=201)
def operator_create_grant(body: AdminGrantRequest, user: access.StoredUser = Depends(require_access_user)):
    _require_review_operator(user)
    try:
        eid = admin_grants.grant(body.workspace_site_id, user.id, body.reason, body.days)
        return {"id": str(eid)}
    except admin_grants.GrantConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        logger.exception("Admin grant creation failed")
        raise HTTPException(status_code=503, detail="No pudimos habilitar el acceso.") from None

@router.post("/operator/grants/{entitlement_id}/revoke")
def operator_revoke_grant(entitlement_id: UUID, body: AdminRevokeRequest, user: access.StoredUser = Depends(require_access_user)):
    _require_review_operator(user)
    try:
        admin_grants.revoke(entitlement_id, user.id, body.reason)
        return {"status": "revoked"}
    except admin_grants.GrantConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception:
        logger.exception("Admin grant revocation failed")
        raise HTTPException(status_code=503, detail="No pudimos revocar el acceso.") from None
