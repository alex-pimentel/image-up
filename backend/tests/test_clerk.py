"""Unit tests for the Clerk JWT verifier (local JWKS verification, no network)."""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import ClerkAuthError, ClerkNotConfigured, ClerkVerifier

ISSUER = "https://clerk.example.com"
AUDIENCE = "imageup"


class FakeJWKClient:
    def __init__(self, key) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, _token: str):
        from types import SimpleNamespace

        return SimpleNamespace(key=self._key)


@pytest.fixture(scope="module")
def keypair():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private, private.public_key()


def make_token(private, **overrides) -> str:
    now = int(time.time())
    payload = {
        "sub": "user_123",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 60,
    }
    payload.update(overrides)
    return jwt.encode(
        payload, private, algorithm="RS256", headers={"kid": "test-key", "alg": "RS256"}
    )


def make_verifier(public) -> ClerkVerifier:
    return ClerkVerifier(
        jwks_url=f"{ISSUER}/.well-known/jwks.json",
        issuer=ISSUER,
        audience=AUDIENCE,
        jwk_client=FakeJWKClient(public),
    )


def test_verify_valid_token_returns_claims(keypair) -> None:
    private, public = keypair
    claims = make_verifier(public).verify(make_token(private))
    assert claims["sub"] == "user_123"


def test_verify_rejects_expired_token(keypair) -> None:
    private, public = keypair
    now = int(time.time())
    with pytest.raises(ClerkAuthError):
        make_verifier(public).verify(make_token(private, iat=now - 120, exp=now - 60))


def test_verify_rejects_wrong_audience(keypair) -> None:
    private, public = keypair
    with pytest.raises(ClerkAuthError):
        make_verifier(public).verify(make_token(private, aud="someone-else"))


def test_verify_rejects_wrong_issuer(keypair) -> None:
    private, public = keypair
    with pytest.raises(ClerkAuthError):
        make_verifier(public).verify(
            make_token(private, iss="https://evil.example.com")
        )


def test_verify_rejects_bad_signature(keypair) -> None:
    _, public = keypair
    other_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(ClerkAuthError):
        make_verifier(public).verify(make_token(other_private))


def test_verify_requires_configuration() -> None:
    verifier = ClerkVerifier(jwks_url=None, issuer=None, audience=None)
    assert verifier.enabled is False
    with pytest.raises(ClerkNotConfigured):
        verifier.verify("some-token")
