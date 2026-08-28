import pytest

from app.integration.mural import access_request_service, exceptions, models
from tests.fakes import in_memory_board_access_request_store


@pytest.fixture
def store() -> in_memory_board_access_request_store.InMemoryBoardAccessRequestStore:
    return in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()


@pytest.fixture
def service(
    store: in_memory_board_access_request_store.InMemoryBoardAccessRequestStore,
) -> access_request_service.BoardAccessRequestService:
    return access_request_service.BoardAccessRequestService(store)


class TestRequestAccess:
    async def test_creates_a_pending_request(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        request = await service.request_access(
            "usr_abc", "board-1", "owner@x.com", "why"
        )

        assert request.user_id == "usr_abc"
        assert request.board_id == "board-1"
        assert request.iao == "owner@x.com"
        assert request.reason == "why"
        assert request.status == models.AccessRequestStatus.PENDING
        assert request.approved is False

    async def test_rejects_a_duplicate_open_request(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        await service.request_access("usr_abc", "board-1", "owner@x.com", "why")

        with pytest.raises(exceptions.AccessRequestAlreadyOpenError):
            await service.request_access("usr_abc", "board-1", "owner@x.com", "again")

    async def test_allowed_again_after_rejection(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        first = await service.request_access("usr_abc", "board-1", "owner@x.com", "why")
        await service.reject(first.id, "reviewer_1", "not now")

        second = await service.request_access(
            "usr_abc", "board-1", "owner@x.com", "why again"
        )

        assert second.id != first.id
        assert second.status == models.AccessRequestStatus.PENDING


class TestGetForUser:
    async def test_returns_the_latest_request(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        await service.request_access("usr_abc", "board-1", "owner@x.com", "why")

        found = await service.get_for_user("usr_abc", "board-1")

        assert found is not None
        assert found.board_id == "board-1"

    async def test_none_when_no_request(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        assert await service.get_for_user("usr_abc", "board-1") is None


class TestListPending:
    async def test_only_returns_pending(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        a = await service.request_access("usr_a", "board-1", "owner@x.com", "why")
        await service.request_access("usr_b", "board-2", "owner@x.com", "why")
        await service.approve(a.id, "reviewer_1", "ok", "form-ref", "risk-ref")

        pending = await service.list_pending()

        assert len(pending) == 1
        assert pending[0].user_id == "usr_b"


class TestApprove:
    async def test_records_the_full_decision(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        request = await service.request_access(
            "usr_abc", "board-1", "owner@x.com", "why"
        )

        approved = await service.approve(
            request.id, "reviewer_1", "looks fine", "form-ref-1", "risk-ref-1"
        )

        assert approved.status == models.AccessRequestStatus.APPROVED
        assert approved.approved is True
        assert approved.reviewer_id == "reviewer_1"
        assert approved.decision_reason == "looks fine"
        assert approved.data_handling_form_ref == "form-ref-1"
        assert approved.risk_assessment_ref == "risk-ref-1"
        assert approved.decided_at is not None

    async def test_unknown_request_raises_not_found(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        with pytest.raises(exceptions.AccessRequestNotFoundError):
            await service.approve("nonexistent", "reviewer_1", "ok", "form", "risk")

    async def test_an_already_decided_request_raises(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        request = await service.request_access(
            "usr_abc", "board-1", "owner@x.com", "why"
        )
        await service.approve(request.id, "reviewer_1", "ok", "form", "risk")

        with pytest.raises(exceptions.AccessRequestAlreadyDecidedError):
            await service.approve(request.id, "reviewer_1", "ok again", "form", "risk")


class TestReject:
    async def test_records_the_decision(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        request = await service.request_access(
            "usr_abc", "board-1", "owner@x.com", "why"
        )

        rejected = await service.reject(request.id, "reviewer_1", "not justified")

        assert rejected.status == models.AccessRequestStatus.REJECTED
        assert rejected.reviewer_id == "reviewer_1"
        assert rejected.decision_reason == "not justified"
        assert rejected.decided_at is not None

    async def test_unknown_request_raises_not_found(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        with pytest.raises(exceptions.AccessRequestNotFoundError):
            await service.reject("nonexistent", "reviewer_1", "no")

    async def test_an_already_decided_request_raises(
        self, service: access_request_service.BoardAccessRequestService
    ) -> None:
        request = await service.request_access(
            "usr_abc", "board-1", "owner@x.com", "why"
        )
        await service.reject(request.id, "reviewer_1", "no")

        with pytest.raises(exceptions.AccessRequestAlreadyDecidedError):
            await service.reject(request.id, "reviewer_1", "no again")
