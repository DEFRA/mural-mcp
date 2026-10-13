"""Boundary tests for app/infra/rest/admin_router.py."""

from app.integration.mural import access_request_service as service_module
from tests.support.app import rest_client, seed

_REVIEWER_EXTERNAL_ID = "reviewer@example.com"


def _headers() -> dict[str, str]:
    return {"X-User-Id": _REVIEWER_EXTERNAL_ID}


def _seed_pending_request(client, overrides):
    """Seed through a real BoardAccessRequestService bound to the app's own
    store, run on the TestClient's own loop (never a bare asyncio.run()) --
    the store is a plain dict fake today, but seeding off-loop would break
    silently the day it holds an asyncio.Lock."""
    service = service_module.BoardAccessRequestService(overrides.access_requests)
    return seed(
        client, service.request_access, "a@example.com", "board-1", "owner@x.com", "why"
    )


class TestListingPendingRequests:
    def test_returns_them(self):
        with rest_client(self_service_access_enabled=True) as (client, overrides):
            _seed_pending_request(client, overrides)

            response = client.get("/admin/access-requests", headers=_headers())

            assert response.status_code == 200
            body = response.json()
            assert len(body) == 1
            assert body[0]["boardId"] == "board-1"

    def test_without_a_trusted_header_is_rejected(self):
        with rest_client(self_service_access_enabled=True) as (client, _overrides):
            response = client.get("/admin/access-requests")

            assert response.status_code == 400


class TestDataHandlingFlag:
    def test_approval_requires_the_references_when_enabled(self):
        with rest_client(
            self_service_access_enabled=True, data_handling_upload_enabled=True
        ) as (client, overrides):
            request = _seed_pending_request(client, overrides)

            response = client.post(
                f"/admin/access-requests/{request.id}/approve",
                json={"decisionReason": "ok"},
                headers=_headers(),
            )

            assert response.status_code == 422

    def test_approval_needs_no_references_when_disabled(self):
        with rest_client(self_service_access_enabled=True) as (client, overrides):
            request = _seed_pending_request(client, overrides)

            response = client.post(
                f"/admin/access-requests/{request.id}/approve",
                json={"decisionReason": "ok"},
                headers=_headers(),
            )

            assert response.status_code == 200
            assert response.json()["dataHandlingFormRef"] is None

    def test_references_are_discarded_when_disabled(self):
        with rest_client(self_service_access_enabled=True) as (client, overrides):
            request = _seed_pending_request(client, overrides)

            response = client.post(
                f"/admin/access-requests/{request.id}/approve",
                json={
                    "decisionReason": "ok",
                    "dataHandlingFormRef": "form-1",
                    "riskAssessmentRef": "risk-1",
                },
                headers=_headers(),
            )

            assert response.status_code == 200
            assert response.json()["dataHandlingFormRef"] is None
            assert response.json()["riskAssessmentRef"] is None


class TestSelfServiceFlag:
    def test_admin_routes_are_not_mounted_when_disabled(self):
        with rest_client() as (client, _overrides):
            response = client.get("/admin/access-requests", headers=_headers())

            assert response.status_code == 404

    def test_approval_routes_are_not_mounted_when_disabled(self):
        with rest_client() as (client, _overrides):
            response = client.get("/approvals/boards/board-1", headers=_headers())

            assert response.status_code == 404

    def test_token_routes_stay_mounted_when_disabled(self):
        with rest_client() as (client, _overrides):
            response = client.get("/tokens", headers=_headers())

            assert response.status_code == 200


class TestApprove:
    def test_records_the_reviewer_and_reason(self):
        with rest_client(
            self_service_access_enabled=True, data_handling_upload_enabled=True
        ) as (client, overrides):
            request = _seed_pending_request(client, overrides)

            response = client.post(
                f"/admin/access-requests/{request.id}/approve",
                json={
                    "decisionReason": "looks good",
                    "dataHandlingFormRef": "form-1",
                    "riskAssessmentRef": "risk-1",
                },
                headers=_headers(),
            )

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "approved"
            assert body["approved"] is True
            assert body["reviewerId"] == _REVIEWER_EXTERNAL_ID
            assert body["decisionReason"] == "looks good"

    def test_an_unknown_request_is_not_found(self):
        with rest_client(
            self_service_access_enabled=True, data_handling_upload_enabled=True
        ) as (client, _overrides):
            response = client.post(
                "/admin/access-requests/nonexistent/approve",
                json={
                    "decisionReason": "ok",
                    "dataHandlingFormRef": "form-1",
                    "riskAssessmentRef": "risk-1",
                },
                headers=_headers(),
            )

            assert response.status_code == 404

    def test_an_already_decided_request_conflicts(self):
        with rest_client(
            self_service_access_enabled=True, data_handling_upload_enabled=True
        ) as (client, overrides):
            request = _seed_pending_request(client, overrides)
            client.post(
                f"/admin/access-requests/{request.id}/approve",
                json={
                    "decisionReason": "ok",
                    "dataHandlingFormRef": "form-1",
                    "riskAssessmentRef": "risk-1",
                },
                headers=_headers(),
            )

            response = client.post(
                f"/admin/access-requests/{request.id}/approve",
                json={
                    "decisionReason": "ok again",
                    "dataHandlingFormRef": "form-1",
                    "riskAssessmentRef": "risk-1",
                },
                headers=_headers(),
            )

            assert response.status_code == 409


class TestReject:
    def test_records_the_reason(self):
        with rest_client(
            self_service_access_enabled=True, data_handling_upload_enabled=True
        ) as (client, overrides):
            request = _seed_pending_request(client, overrides)

            response = client.post(
                f"/admin/access-requests/{request.id}/reject",
                json={"decisionReason": "not justified"},
                headers=_headers(),
            )

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "rejected"
            assert body["approved"] is False
            assert body["decisionReason"] == "not justified"

    def test_an_unknown_request_is_not_found(self):
        with rest_client(
            self_service_access_enabled=True, data_handling_upload_enabled=True
        ) as (client, _overrides):
            response = client.post(
                "/admin/access-requests/nonexistent/reject",
                json={"decisionReason": "no"},
                headers=_headers(),
            )

            assert response.status_code == 404
