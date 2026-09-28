"""Mininode Access identity and authorization endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from mininode_api.core.access_auth import require_access_user
from mininode_api.services import access

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
