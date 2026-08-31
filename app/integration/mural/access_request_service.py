import datetime
import uuid

from app.integration.mural import exceptions, models, ports


class BoardAccessRequestService:
    """The request -> IAO review -> decision workflow backing
    BoardGuard's default AllowListBoardGuard (see guard.py). Routers use
    this, never the store directly.
    """

    def __init__(self, store: ports.BoardAccessRequestStore) -> None:
        self._store = store

    async def request_access(
        self, user_id: str, board_id: str, iao: str, reason: str
    ) -> models.BoardAccessRequest:
        existing = await self._store.get_latest_for_user_and_board(user_id, board_id)
        if (
            existing is not None
            and existing.status != models.AccessRequestStatus.REJECTED
        ):
            msg = f"A pending or approved request already exists for board {board_id}."
            raise exceptions.AccessRequestAlreadyOpenError(msg)

        request = models.BoardAccessRequest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            board_id=board_id,
            iao=iao,
            reason=reason,
            created_at=datetime.datetime.now(datetime.UTC),
        )
        await self._store.create(request)
        return request

    async def get_for_user(
        self, user_id: str, board_id: str
    ) -> models.BoardAccessRequest | None:
        return await self._store.get_latest_for_user_and_board(user_id, board_id)

    async def list_pending(self) -> list[models.BoardAccessRequest]:
        return await self._store.list_pending()

    async def approve(
        self,
        request_id: str,
        reviewer_id: str,
        decision_reason: str,
        data_handling_form_ref: str,
        risk_assessment_ref: str,
    ) -> models.BoardAccessRequest:
        request = await self._get_pending(request_id)
        request.status = models.AccessRequestStatus.APPROVED
        request.reviewer_id = reviewer_id
        request.decision_reason = decision_reason
        request.data_handling_form_ref = data_handling_form_ref
        request.risk_assessment_ref = risk_assessment_ref
        request.decided_at = datetime.datetime.now(datetime.UTC)
        await self._store.update(request)
        return request

    async def reject(
        self, request_id: str, reviewer_id: str, decision_reason: str
    ) -> models.BoardAccessRequest:
        request = await self._get_pending(request_id)
        request.status = models.AccessRequestStatus.REJECTED
        request.reviewer_id = reviewer_id
        request.decision_reason = decision_reason
        request.decided_at = datetime.datetime.now(datetime.UTC)
        await self._store.update(request)
        return request

    async def _get_pending(self, request_id: str) -> models.BoardAccessRequest:
        request = await self._store.get(request_id)

        if request is None:
            msg = f"No access request {request_id}"
            raise exceptions.AccessRequestNotFoundError(msg)

        if request.status != models.AccessRequestStatus.PENDING:
            msg = f"Access request {request_id} already {request.status.value}"
            raise exceptions.AccessRequestAlreadyDecidedError(msg)

        return request
