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
    hostname: str


class AccessCompanyContextResponse(BaseModel):
    id: UUID
    name: str
    sites: list[AccessSiteContextResponse]


class AccessWorkspaceContextResponse(BaseModel):
    id: UUID
    name: str
    role: str
    companies: list[AccessCompanyContextResponse]


class AccessContextResponse(BaseModel):
    workspaces: list[AccessWorkspaceContextResponse]


@router.get("/me", response_model=AccessMeResponse)
def access_me(
    user: access.StoredUser = Depends(require_access_user),
) -> AccessMeResponse:
    return AccessMeResponse(user_id=user.id, email=user.email)


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
                companies=[
                    AccessCompanyContextResponse(
                        id=company.id,
                        name=company.name,
                        sites=[
                            AccessSiteContextResponse(
                                id=site.id,
                                hostname=site.hostname,
                            )
                            for site in company.sites
                        ],
                    )
                    for company in workspace.companies
                ],
            )
            for workspace in workspaces
        ]
    )
