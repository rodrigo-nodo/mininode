"""Mininode Access identity endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from mininode_api.services import access, access_identity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/access", tags=["access"])


class AccessMeResponse(BaseModel):
    user_id: UUID
    email: str


@router.get("/me", response_model=AccessMeResponse)
def access_me(
    request: Request,
    cf_access_jwt_assertion: str | None = Header(
        default=None,
        alias="Cf-Access-Jwt-Assertion",
    ),
) -> AccessMeResponse:
    if not request.app.state.access_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        )

    if not cf_access_jwt_assertion:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cloudflare Access identity is required",
        )

    try:
        identity = access_identity.verify_access_jwt(cf_access_jwt_assertion)
    except access_identity.AccessIdentityConfigError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access identity is not configured",
        )
    except access_identity.AccessIdentityUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access identity is temporarily unavailable",
        )
    except access_identity.AccessIdentityInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Cloudflare Access identity",
        )
    except access_identity.AccessIdentityEmailUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cloudflare Access user email is required",
        )

    try:
        user = access.get_or_create_user(identity.email)
    except Exception:
        logger.exception("Access user persistence failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        )

    return AccessMeResponse(user_id=user.id, email=user.email)
