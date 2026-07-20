import fastapi
from dishka.integrations import fastapi as dishka_fastapi

from app.auth import dependencies as auth_deps
from app.mural.board import service as board_service_module
from app.mural.connectivity import exceptions

router = fastapi.APIRouter()


@router.get("/{mural_id}/summary")
@dishka_fastapi.inject
async def get_board_summary(
    mural_id: str,
    user_id: str = fastapi.Depends(auth_deps.get_current_user),
    board: dishka_fastapi.FromDishka[board_service_module.BoardService] = ...,  # type: ignore[assignment]
    use_spatial_grouping: bool = False,
) -> str:
    """Return a compact MSX summary of the board's top-level regions."""
    try:
        return await board.fetch_summary(user_id, mural_id, use_spatial_grouping)
    except exceptions.MuralTokenError as exc:
        raise fastapi.HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{mural_id}/regions/{region_id}")
@dishka_fastapi.inject
async def get_board_region(
    mural_id: str,
    region_id: str,
    user_id: str = fastapi.Depends(auth_deps.get_current_user),
    board: dishka_fastapi.FromDishka[board_service_module.BoardService] = ...,  # type: ignore[assignment]
    use_spatial_grouping: bool = False,
) -> str:
    """Return full MSX for all widgets within a board region."""
    try:
        return await board.fetch_region(
            user_id, mural_id, region_id, use_spatial_grouping
        )
    except exceptions.MuralTokenError as exc:
        raise fastapi.HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{mural_id}/connections/{widget_id}")
@dishka_fastapi.inject
async def get_widget_connections(
    mural_id: str,
    widget_id: str,
    user_id: str = fastapi.Depends(auth_deps.get_current_user),
    board: dishka_fastapi.FromDishka[board_service_module.BoardService] = ...,  # type: ignore[assignment]
) -> str:
    """Return all arrows connected to a widget and their resolved endpoints."""
    try:
        return await board.fetch_connections(user_id, mural_id, widget_id)
    except exceptions.MuralTokenError as exc:
        raise fastapi.HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{mural_id}/widgets")
@dishka_fastapi.inject
async def find_board_widgets(
    mural_id: str,
    user_id: str = fastapi.Depends(auth_deps.get_current_user),
    board: dishka_fastapi.FromDishka[board_service_module.BoardService] = ...,  # type: ignore[assignment]
    query: str | None = None,
    widget_type: str | None = None,
) -> str:
    """Search board widgets by text content and/or widget type."""
    if not query and not widget_type:
        raise fastapi.HTTPException(
            status_code=422, detail="Provide at least one of: query, widget_type."
        )

    try:
        return await board.search_widgets(user_id, mural_id, query, widget_type)
    except exceptions.MuralTokenError as exc:
        raise fastapi.HTTPException(status_code=409, detail=str(exc)) from exc
