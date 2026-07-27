import datetime

import fastapi
import pydantic
from dishka.integrations import fastapi as dishka_fastapi

from app.auth import dependencies as auth_deps
from app.mural.board.approval import models, ports

router = fastapi.APIRouter()


class CreateBoardApprovalPayload(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(populate_by_name=True)

    board_id: str = pydantic.Field(alias="boardId")
    iao: str


class BoardApprovalResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(populate_by_name=True)

    board_id: str = pydantic.Field(serialization_alias="boardId")
    iao: str
    email: str
    status: str
    submitted_at: datetime.datetime = pydantic.Field(serialization_alias="submittedAt")
    approved: bool

    @classmethod
    def from_domain(cls, approval: models.BoardApproval) -> "BoardApprovalResponse":
        return cls(
            board_id=approval.board_id,
            iao=approval.iao,
            email=approval.email,
            status=approval.status,
            submitted_at=approval.submitted_at,
            approved=approval.approved,
        )


@router.post("/boards", status_code=201)
@dishka_fastapi.inject
async def create_board_approval(
    payload: CreateBoardApprovalPayload,
    user_id: str = fastapi.Depends(auth_deps.get_current_user),
    store: dishka_fastapi.FromDishka[ports.BoardApprovalStore] = ...,  # type: ignore[assignment]
) -> BoardApprovalResponse:
    if await store.exists_open(payload.board_id):
        raise fastapi.HTTPException(
            status_code=409, detail="A pending request already exists for this board."
        )

    approval = models.BoardApproval(
        board_id=payload.board_id,
        iao=payload.iao,
        email=user_id,
        submitted_at=datetime.datetime.now(datetime.UTC),
    )
    await store.create(approval)
    return BoardApprovalResponse.from_domain(approval)


@router.get("/boards/{board_id}")
@dishka_fastapi.inject
async def get_board_approval(
    board_id: str,
    user_id: str = fastapi.Depends(auth_deps.get_current_user),
    store: dishka_fastapi.FromDishka[ports.BoardApprovalStore] = ...,  # type: ignore[assignment]
) -> BoardApprovalResponse:
    approval = await store.get_by_board_id(board_id, user_id)
    if approval is None:
        raise fastapi.HTTPException(status_code=404, detail="Board approval not found.")
    return BoardApprovalResponse.from_domain(approval)
