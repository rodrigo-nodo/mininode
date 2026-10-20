"""Mininode Access identity and authorization endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from mininode_api.core.access_auth import require_access_user
from mininode_api.services import access, site_group_reviews

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
    except access.ActiveSiteCannotBeUnlinked:
        raise HTTPException(status_code=409, detail="Este sitio tiene una contratación o compra pendiente y no puede desvincularse.")
    except Exception:
        logger.exception("Access site unlink failed")
        raise HTTPException(status_code=503, detail="El servicio de acceso no está disponible.")
    if not found:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
