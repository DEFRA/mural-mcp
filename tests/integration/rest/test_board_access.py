"""Boundary tests for app/infra/rest/approval_router.py."""

import datetime

from app.integration.mural import models
from tests.support.app import rest_client, seed

_EXTERNAL_ID = "user@example.com"
_PAYLOAD = {"boardId": "board-abc", "iao": "owner@defra.gov.uk", "reason": "need it"}


def _headers() -> dict[str, str]:
    return {"X-User-Id": _EXTERNAL_ID}


class TestRequestingAccess:
    def test_creates_a_pending_request(self):
        with rest_client() as (client, _overrides):
            response = client.post(
                "/approvals/boards", json=_PAYLOAD, headers=_headers()
            )

            assert response.status_code == 201
            body = response.json()
            assert body["boardId"] == "board-abc"
            assert body["iao"] == "owner@defra.gov.uk"
            assert body["reason"] == "need it"
            assert body["status"] == "pending"
            assert body["approved"] is False

    def test_conflicts_when_the_same_board_is_already_requested(self):
        with rest_client() as (client, _overrides):
            client.post("/approvals/boards", json=_PAYLOAD, headers=_headers())

            response = client.post(
                "/approvals/boards", json=_PAYLOAD, headers=_headers()
            )

            assert response.status_code == 409

    def test_is_rejected_without_a_trusted_header(self):
        with rest_client() as (client, _overrides):
            response = client.post("/approvals/boards", json=_PAYLOAD)

            assert response.status_code == 400


class TestGettingARequest:
    def test_returns_a_requested_board(self):
        with rest_client() as (client, _overrides):
            client.post("/approvals/boards", json=_PAYLOAD, headers=_headers())

            response = client.get("/approvals/boards/board-abc", headers=_headers())

            assert response.status_code == 200
            assert response.json()["boardId"] == "board-abc"

    def test_is_not_found_when_never_requested(self):
        with rest_client() as (client, _overrides):
            response = client.get("/approvals/boards/nonexistent", headers=_headers())

            assert response.status_code == 404

    def test_is_scoped_to_the_requesting_user(self):
        with rest_client() as (client, overrides):
            other_users_request = models.BoardAccessRequest(
                id="req-other",
                user_id="usr_other",
                board_id="board-abc",
                reason="need it",
                iao="owner@defra.gov.uk",
                created_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
            )
            seed(client, overrides.access_requests.create, other_users_request)

            response = client.get("/approvals/boards/board-abc", headers=_headers())

            assert response.status_code == 404
