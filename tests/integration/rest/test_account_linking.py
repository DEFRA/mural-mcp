"""Boundary tests for the Mural OAuth callback (app/infra/rest/linking_router.py).

This is the far end of the repo's one real multi-surface journey: an MCP
tool issues the OAuth state, this REST route consumes it. The cross-user
403 here is what tests/unit/auth/test_cross_surface_identity.py's invariant
exists to protect -- until this file, nothing drove the guarded code
itself, only the guard.
"""

import datetime

import httpx

from app.identity import models as identity_models
from tests.support.app import rest_client, seed

_EXTERNAL_ID = "user@example.com"
_MURAL_TOKEN_RESPONSE = httpx.Response(
    200,
    json={
        "access_token": "mural-access-token",
        "refresh_token": "mural-refresh-token",
        "expires_in": 3600,
    },
)


def _headers(external_id: str = _EXTERNAL_ID) -> dict[str, str]:
    return {"X-User-Id": external_id}


def _seed_user(client, overrides, *, user_id: str, external_id: str) -> None:
    """Pre-create the identity a trusted X-User-Id header resolves to, so the
    test controls the internal user_id instead of discovering a minted one."""
    seed(
        client,
        overrides.users.create,
        identity_models.User(
            user_id=user_id,
            external_id=external_id,
            email=external_id,
            created_at=datetime.datetime.now(datetime.UTC),
        ),
    )


class TestCallback:
    def test_completing_it_stores_tokens_for_the_issuing_user(self):
        with rest_client(responses=[_MURAL_TOKEN_RESPONSE]) as (client, overrides):
            _seed_user(client, overrides, user_id="usr_abc", external_id=_EXTERNAL_ID)
            state = seed(client, overrides.states.issue, "usr_abc")

            response = client.get(
                "/linking/callback",
                params={"code": "auth-code", "state": state},
                headers=_headers(),
            )

            assert response.status_code == 200
            assert response.json() == {"status": "success"}
            stored = seed(client, overrides.tokens.get_tokens, "usr_abc")
            assert stored is not None
            assert stored.access_token == "mural-access-token"

    def test_a_replayed_or_forged_state_is_rejected(self):
        with rest_client() as (client, _overrides):
            response = client.get(
                "/linking/callback",
                params={"code": "auth-code", "state": "not-a-real-state"},
                headers=_headers(),
            )

            assert response.status_code == 400

    def test_another_users_callback_is_forbidden(self):
        with rest_client() as (client, overrides):
            _seed_user(client, overrides, user_id="usr_abc", external_id=_EXTERNAL_ID)
            state = seed(client, overrides.states.issue, "someone-else")

            response = client.get(
                "/linking/callback",
                params={"code": "auth-code", "state": state},
                headers=_headers(),
            )

            assert response.status_code == 403
            assert seed(client, overrides.tokens.get_tokens, "usr_abc") is None


class TestStatus:
    def test_reports_not_linked_before_connecting(self):
        with rest_client() as (client, _overrides):
            response = client.get("/linking/status", headers=_headers())

            assert response.status_code == 200
            assert response.json() == {"linked": False, "accessTokenExpiresAt": None}

    def test_reports_linked_after_connecting(self):
        with rest_client(responses=[_MURAL_TOKEN_RESPONSE]) as (client, overrides):
            _seed_user(client, overrides, user_id="usr_abc", external_id=_EXTERNAL_ID)
            state = seed(client, overrides.states.issue, "usr_abc")
            client.get(
                "/linking/callback",
                params={"code": "auth-code", "state": state},
                headers=_headers(),
            )

            response = client.get("/linking/status", headers=_headers())

            data = response.json()
            assert data["linked"] is True
            assert data["accessTokenExpiresAt"] is not None


class TestTestConnection:
    def test_returns_401_if_not_linked(self):
        with rest_client() as (client, _overrides):
            response = client.get("/linking/test-connection", headers=_headers())

            assert response.status_code == 401
            assert "does not have a valid access token" in response.json()["detail"]

    def test_returns_200_if_linked_and_mural_accepts_token(self):
        """When the user is linked and Mural's /users/me call succeeds."""
        mural_responses = [
            _MURAL_TOKEN_RESPONSE,  # for the callback (storing the token)
            httpx.Response(
                200, json={"value": {"id": "mural_u123"}}
            ),  # for test-connection
        ]
        with rest_client(responses=mural_responses) as (client, overrides):
            _seed_user(client, overrides, user_id="usr_abc", external_id=_EXTERNAL_ID)
            state = seed(client, overrides.states.issue, "usr_abc")
            # Link the account first
            client.get(
                "/linking/callback",
                params={"code": "auth-code", "state": state},
                headers=_headers(),
            )

            response = client.get("/linking/test-connection", headers=_headers())

            assert response.status_code == 200
            assert response.json() == {"status": "success"}

    def test_returns_401_if_mural_rejects_token(self):
        """When the user is linked but Mural returns 401 (token revoked/expired)."""
        mural_responses = [
            _MURAL_TOKEN_RESPONSE,  # for the callback
            httpx.Response(401),  # for test-connection (Mural rejects the token)
        ]
        with rest_client(responses=mural_responses) as (client, overrides):
            _seed_user(client, overrides, user_id="usr_abc", external_id=_EXTERNAL_ID)
            state = seed(client, overrides.states.issue, "usr_abc")
            client.get(
                "/linking/callback",
                params={"code": "auth-code", "state": state},
                headers=_headers(),
            )

            response = client.get("/linking/test-connection", headers=_headers())

            assert response.status_code == 401
            assert "rejected the access token" in response.json()["detail"]

    def test_returns_502_if_mural_server_error(self):
        """When Mural returns a 5xx error."""
        mural_responses = [
            _MURAL_TOKEN_RESPONSE,  # for the callback
            httpx.Response(500),  # for test-connection (Mural server error)
        ]
        with rest_client(responses=mural_responses) as (client, overrides):
            _seed_user(client, overrides, user_id="usr_abc", external_id=_EXTERNAL_ID)
            state = seed(client, overrides.states.issue, "usr_abc")
            client.get(
                "/linking/callback",
                params={"code": "auth-code", "state": state},
                headers=_headers(),
            )

            response = client.get("/linking/test-connection", headers=_headers())

            assert response.status_code == 502
            # MuralApiError includes the status code in its message
            assert "status" in response.json()["detail"].lower()

    def test_returns_502_if_mural_is_unreachable(self):
        """When the request to Mural fails before any response is received
        (e.g. Mural is down, DNS failure, connection timeout)."""
        mural_responses = [
            _MURAL_TOKEN_RESPONSE,  # for the callback
            httpx.ConnectError("Connection refused"),  # for test-connection
        ]
        with rest_client(responses=mural_responses) as (client, overrides):
            _seed_user(client, overrides, user_id="usr_abc", external_id=_EXTERNAL_ID)
            state = seed(client, overrides.states.issue, "usr_abc")
            client.get(
                "/linking/callback",
                params={"code": "auth-code", "state": state},
                headers=_headers(),
            )

            response = client.get("/linking/test-connection", headers=_headers())

            assert response.status_code == 502
            assert response.json() == {"detail": "Mural API is unreachable"}
