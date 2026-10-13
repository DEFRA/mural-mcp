import pytest

from app.identity import service as identity_service
from app.infra.auth import personal_token
from tests.fakes import in_memory_identity_store

_PREFIX = "mmcp_"


@pytest.fixture
def pat_store() -> in_memory_identity_store.InMemoryPersonalAccessTokenStore:
    return in_memory_identity_store.InMemoryPersonalAccessTokenStore()


@pytest.fixture
def tokens(
    pat_store: in_memory_identity_store.InMemoryPersonalAccessTokenStore,
) -> identity_service.PersonalTokenService:
    return identity_service.PersonalTokenService(
        pat_store,
        token_prefix=_PREFIX,
        default_ttl_days=90,
        max_ttl_days=365,
        last_used_throttle_seconds=300,
    )


@pytest.fixture
def verifier(
    tokens: identity_service.PersonalTokenService,
) -> personal_token.PersonalTokenVerifier:
    return personal_token.PersonalTokenVerifier(tokens)


class TestVerify:
    async def test_returns_claims_for_a_valid_token(
        self,
        verifier: personal_token.PersonalTokenVerifier,
        tokens: identity_service.PersonalTokenService,
    ) -> None:
        _, secret = await tokens.mint("a@example.com", "Claude Code")

        result = await verifier.verify(secret)

        assert result is not None
        assert result.claims["sub"] == "a@example.com"
        assert result.claims["email"] == "a@example.com"
        assert result.claims["label"] == "Claude Code"

    async def test_returns_none_for_unknown_token(
        self, verifier: personal_token.PersonalTokenVerifier
    ) -> None:
        assert await verifier.verify(f"{_PREFIX}garbage") is None

    async def test_returns_none_for_revoked_token(
        self,
        verifier: personal_token.PersonalTokenVerifier,
        tokens: identity_service.PersonalTokenService,
    ) -> None:
        record, secret = await tokens.mint("a@example.com", "Claude Code")
        await tokens.revoke("a@example.com", record.id)

        assert await verifier.verify(secret) is None
