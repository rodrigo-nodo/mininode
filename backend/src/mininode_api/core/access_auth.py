"""Reusable authenticated-user dependency for Mininode Access."""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, Request, status

from mininode_api.services import access, access_identity

logger = logging.getLogger(__name__)


def require_access_user(
    request: Request,
    cf_access_jwt_assertion: str | None = Header(
        default=None,
        alias="Cf-Access-Jwt-Assertion",
    ),
) -> access.StoredUser:
    """Resolve a verified Cloudflare identity to the canonical Mininode user."""

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
        return access.get_or_create_user(identity.email)
    except Exception:
        logger.exception("Access user persistence failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        )
