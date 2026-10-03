"""Optional Clerk JWT verification.

Tokens are verified locally against Clerk's JWKS — no per-request call to Clerk
and no secret key required for read-only verification. Authentication is
optional: a missing token means "anonymous" (stricter limits); a malformed or
invalid token is rejected with 401.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Header, HTTPException, status

from .config import settings

logger = logging.getLogger(__name__)

ALGORITHMS = ("RS256",)


class ClerkNotConfigured(RuntimeError):
    """Raised when verification is attempted without a JWKS URL."""


class ClerkAuthError(Exception):
    """Raised when a token fails verification."""


class ClerkVerifier:
    def __init__(
        self,
        *,
        jwks_url: str | None = None,
        issuer: str | None = None,
        audience: str | None = None,
        jwk_client: Any | None = None,
    ) -> None:
        self._jwks_url = jwks_url
        self._issuer = issuer or None
        self._audience = audience or None
        self._jwk_client = jwk_client

    @property
    def enabled(self) -> bool:
        return bool(self._jwks_url)

    @property
    def jwk_client(self) -> Any:
        if self._jwk_client is None:
            from jwt import PyJWKClient  # imported lazily so fallback mode stays light

            if not self._jwks_url:
                raise ClerkNotConfigured("CLERK_JWKS_URL is not configured")
            self._jwk_client = PyJWKClient(self._jwks_url)
        return self._jwk_client

    def verify(self, token: str) -> dict[str, Any]:
        if not self.enabled:
            raise ClerkNotConfigured("CLERK_JWKS_URL is not configured")
        import jwt

        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=list(ALGORITHMS),
                issuer=self._issuer,
                audience=self._audience,
                options={"verify_aud": self._audience is not None},
            )
        except ClerkNotConfigured:
            raise
        except Exception as e:  # any JWT failure is an auth failure
            raise ClerkAuthError(str(e)) from e


_verifier: ClerkVerifier | None = None


def get_verifier() -> ClerkVerifier:
    global _verifier
    if _verifier is None:
        _verifier = ClerkVerifier(
            jwks_url=settings.clerk_jwks_url,
            issuer=settings.clerk_issuer,
            audience=settings.clerk_audience,
        )
    return _verifier


async def optional_clerk_user(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    """FastAPI dependency returning verified Clerk claims, or ``None`` for anonymous."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )
    verifier = get_verifier()
    if not verifier.enabled:
        # Auth is not configured: degrade to anonymous rather than block usage.
        return None
    try:
        return verifier.verify(token.strip())
    except ClerkAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        ) from e
