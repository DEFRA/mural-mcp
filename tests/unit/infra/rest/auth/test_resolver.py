import fastapi
import pytest

from app.auth import verifier as verifier_port
from app.infra.rest.auth import resolver


def _make_request(headers: dict[str, str] | None = None) -> fastapi.Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": raw_headers,
    }
    return fastapi.Request(scope)


class _FakeVerifier:
    def __init__(self, result: verifier_port.VerifiedToken | None) -> None:
        self._result = result

    async def verify(self, token: str) -> verifier_port.VerifiedToken | None:  # noqa: ARG002
        return self._result


class TestTrustedHeaderUserResolver:
    async def test_the_asserted_email_is_the_user_id(self) -> None:
        resolver_under_test = resolver.TrustedHeaderUserResolver("X-User-Id")

        principal = await resolver_under_test.resolve(
            _make_request({"X-User-Id": "dev@example.com"})
        )

        assert principal.email == "dev@example.com"
        assert principal.user_id == "dev@example.com"
        assert principal.scopes == frozenset()

    async def test_normalises_case_and_whitespace(self) -> None:
        resolver_under_test = resolver.TrustedHeaderUserResolver("X-User-Id")

        principal = await resolver_under_test.resolve(
            _make_request({"X-User-Id": "  Dev@Example.com "})
        )

        assert principal.user_id == "dev@example.com"

    async def test_requires_the_header(self) -> None:
        resolver_under_test = resolver.TrustedHeaderUserResolver("X-User-Id")

        with pytest.raises(fastapi.HTTPException) as exc_info:
            await resolver_under_test.resolve(_make_request())
        assert exc_info.value.status_code == 400

    async def test_rejects_a_blank_header(self) -> None:
        resolver_under_test = resolver.TrustedHeaderUserResolver("X-User-Id")

        with pytest.raises(fastapi.HTTPException) as exc_info:
            await resolver_under_test.resolve(_make_request({"X-User-Id": "   "}))
        assert exc_info.value.status_code == 400


class TestPersonalTokenUserResolver:
    async def test_builds_principal_from_claims(self) -> None:
        fake = _FakeVerifier(
            verifier_port.VerifiedToken(
                claims={
                    "sub": "abc@example.com",
                    "email": "a@example.com",
                    "label": "Claude Code",
                    "token_id": "pat_1",
                }
            )
        )
        resolver_under_test = resolver.PersonalTokenUserResolver(fake)

        principal = await resolver_under_test.resolve(
            _make_request({"Authorization": "Bearer mmcp_something"})
        )

        assert principal.user_id == "abc@example.com"
        assert principal.email == "a@example.com"
        assert principal.label == "Claude Code"
        assert principal.token_id == "pat_1"

    async def test_requires_bearer_header(self) -> None:
        resolver_under_test = resolver.PersonalTokenUserResolver(_FakeVerifier(None))

        with pytest.raises(fastapi.HTTPException) as exc_info:
            await resolver_under_test.resolve(_make_request())
        assert exc_info.value.status_code == 401

    async def test_rejects_an_unverifiable_token(self) -> None:
        resolver_under_test = resolver.PersonalTokenUserResolver(_FakeVerifier(None))

        with pytest.raises(fastapi.HTTPException) as exc_info:
            await resolver_under_test.resolve(
                _make_request({"Authorization": "Bearer mmcp_bad"})
            )
        assert exc_info.value.status_code == 401
