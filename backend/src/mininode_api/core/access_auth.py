"""Reusable authenticated-user dependency for Mininode Access."""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, Request, status

from mininode_api.services import access, access_identity, clerk_identity

logger = logging.getLogger(__name__)


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )
    return token.strip()


def _verified_email(
    *,
    authorization: str | None,
    cf_access_jwt_assertion: str | None,
) -> str:
    """Resolve exactly one verified identity provider.

    Clerk Bearer tokens take precedence during the migration. Cloudflare Access
    remains a fallback only when no Authorization header is present, so a failed
    Clerk verification can never silently fall back to another identity.
    """

    clerk_token = _bearer_token(authorization)
    if clerk_token is not None:
        try:
            return clerk_identity.verify_clerk_session(clerk_token).email
        except clerk_identity.ClerkIdentityConfigError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Clerk identity is not configured",
            )
        except clerk_identity.ClerkIdentityUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Clerk identity is temporarily unavailable",
            )
        except clerk_identity.ClerkIdentityInvalidError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Clerk identity",
            )
        except clerk_identity.ClerkIdentityEmailUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clerk user email is required",
            )

    if not cf_access_jwt_assertion:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated identity is required",
        )

    try:
        return access_identity.verify_access_jwt(cf_access_jwt_assertion).email
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


def require_access_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    cf_access_jwt_assertion: str | None = Header(
        default=None,
        alias="Cf-Access-Jwt-Assertion",
    ),
) -> access.StoredUser:
    """Resolve a verified external identity to the canonical Mininode user."""

    if not request.app.state.access_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        )

    email = _verified_email(
        authorization=authorization,
        cf_access_jwt_assertion=cf_access_jwt_assertion,
    )

    try:
        return access.get_or_create_user(email)
    except Exception:
        logger.exception("Access user persistence failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access is temporarily unavailable",
        )
