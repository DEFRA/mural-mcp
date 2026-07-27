import contextlib
from collections.abc import AsyncIterator

import dishka

from app.auth import service as bearer_service
from app.mural.board import registry as widget_registry
from app.mural.board.approval import ports as approval_ports
from app.mural.board.renderers import msx as widget_msx
from app.mural.board.summary import renderer as summary_renderer
from app.mural.connectivity import ports as token_store
from app.mural.connectivity import state_store
from tests.fakes import (
    in_memory_approval_store,
    in_memory_bearer_service,
    in_memory_token_store,
)


class TestProvider(dishka.Provider):
    """APP-scoped provider that substitutes in-memory fakes for all persistence."""

    scope = dishka.Scope.APP

    @dishka.provide
    def provide_token_store(self) -> token_store.TokenStore:
        return in_memory_token_store.InMemoryTokenStore()

    @dishka.provide
    def provide_bearer_service(self) -> bearer_service.BearerTokenService:
        return in_memory_bearer_service.InMemoryBearerTokenService()

    @dishka.provide
    def provide_board_approval_store(self) -> approval_ports.BoardApprovalStore:
        return in_memory_approval_store.InMemoryBoardApprovalStore()

    @dishka.provide
    def provide_state_store(self) -> state_store.OAuthStateStore:
        return state_store.OAuthStateStore()

    @dishka.provide
    def provide_registry(self) -> widget_registry.WidgetRendererRegistry:
        return widget_registry.build_default_registry()

    @dishka.provide
    def provide_msx_renderer(
        self,
        reg: widget_registry.WidgetRendererRegistry,
    ) -> widget_msx.WidgetMsxRenderer:
        return widget_msx.WidgetMsxRenderer(reg)

    @dishka.provide
    def provide_summary_msx_renderer(
        self,
        reg: widget_registry.WidgetRendererRegistry,
    ) -> summary_renderer.SummaryMsxRenderer:
        return summary_renderer.SummaryMsxRenderer(reg)


@contextlib.asynccontextmanager
async def build_test_container() -> AsyncIterator[dishka.AsyncContainer]:
    async with dishka.make_async_container(TestProvider()) as container:
        yield container
