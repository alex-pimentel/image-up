"""Tests for the optional Clerk auth dependency and verifier wiring."""

from __future__ import annotations

import asyncio
import dataclasses

import pytest
from fastapi import HTTPException

from app import auth as auth_module
from app.auth import (
    ClerkAuthError,
    ClerkNotConfigured,
    ClerkVerifier,
    get_verifier,
    optional_clerk_user,
)


class _RaisingJWKClient:
    def get_signing_key_from_jwt(self, _token: str):
        raise ClerkNotConfigured("no jwks")


class _BoomVerifier:
    enabled = True

    def verify(self, _token: str):
        raise ClerkAuthError("bad token")


class _OkVerifier:
    enabled = True

    def verify(self, _token: str):
        return {"sub": "user_1"}


def test_jwk_client_is_lazy_and_requires_url() -> None:
    client = ClerkVerifier(jwks_url="https://clerk.example.com/jwks.json").jwk_client
    assert client is not None

    with pytest.raises(ClerkNotConfigured):
        _ = ClerkVerifier().jwk_client


def test_verify_reraises_not_configured() -> None:
    verifier = ClerkVerifier(
        jwks_url="https://x/jwks.json", jwk_client=_RaisingJWKClient()
    )
    with pytest.raises(ClerkNotConfigured):
        verifier.verify("token")


def test_get_verifier_is_a_singleton(monkeypatch) -> None:
    new_settings = dataclasses.replace(
        auth_module.settings,
        clerk_jwks_url="https://clerk.example.com/jwks.json",
        clerk_issuer="https://clerk.example.com",
        clerk_audience="imageup",
    )
    monkeypatch.setattr(auth_module, "settings", new_settings)
    monkeypatch.setattr(auth_module, "_verifier", None)

    first = get_verifier()
    assert first.enabled is True
    assert get_verifier() is first


def test_optional_user_anonymous_without_header() -> None:
    assert asyncio.run(optional_clerk_user(None)) is None


@pytest.mark.parametrize("header", ["Token abc", "Bearer ", "Basic xyz"])
def test_optional_user_rejects_bad_header(header: str) -> None:
    with pytest.raises(HTTPException) as exc:
        asyncio.run(optional_clerk_user(header))
    assert exc.value.status_code == 401


def test_optional_user_degrades_when_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(auth_module, "get_verifier", lambda: ClerkVerifier())
    assert asyncio.run(optional_clerk_user("Bearer token")) is None


def test_optional_user_rejects_invalid_token(monkeypatch) -> None:
    monkeypatch.setattr(auth_module, "get_verifier", lambda: _BoomVerifier())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(optional_clerk_user("Bearer token"))
    assert exc.value.status_code == 401


def test_optional_user_returns_claims(monkeypatch) -> None:
    monkeypatch.setattr(auth_module, "get_verifier", lambda: _OkVerifier())
    assert asyncio.run(optional_clerk_user("Bearer token")) == {"sub": "user_1"}
