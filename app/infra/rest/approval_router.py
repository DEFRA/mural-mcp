import fastapi
import pydantic
from dishka.integrations import fastapi as dishka_fastapi

from app.auth import principal as principal_module
from app.infra.rest.auth import dependencies as auth_deps
from app.integration.mural import access_request_service, exceptions
from app.integration.mural import models as access_request_models

router = fastapi.APIRouter()


class RequestBoardAccessPayload(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(populate_by_name=True)

    board_id: str = pydantic.Field(alias="boardId")
    iao: str
    reason: str


@router.post("/boards", status_code=201)
@dishka_fastapi.inject
async def request_board_access(
    payload: RequestBoardAccessPayload,
    principal: principal_module.Principal = fastapi.Depends(auth_deps.get_principal),
    service: dishka_fastapi.FromDishka[
        access_request_service.BoardAccessRequestService
    ] = ...,  # type: ignore[assignment]
) -> access_request_models.BoardAccessRequest:
    try:
        return await service.request_access(
            principal.user_id, payload.board_id, payload.iao, payload.reason
        )
    except exceptions.AccessRequestAlreadyOpenError as exc:
        raise fastapi.HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/boards/{board_id}")
@dishka_fastapi.inject
async def get_board_access_request(
    board_id: str,
    principal: principal_module.Principal = fastapi.Depends(auth_deps.get_principal),
    service: dishka_fastapi.FromDishka[
        access_request_service.BoardAccessRequestService
    ] = ...,  # type: ignore[assignment]
) -> access_request_models.BoardAccessRequest:
    request = await service.get_for_user(principal.user_id, board_id)
    if request is None:
        raise fastapi.HTTPException(
            status_code=404, detail="Board access request not found."
        )
    return request
