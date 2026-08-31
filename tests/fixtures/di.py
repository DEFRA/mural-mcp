import contextlib
from collections.abc import AsyncIterator

import dishka

from app.integration.linking import ports as token_store
from app.integration.mural import guard as guard_module
from app.integration.mural import ports as approval_ports
from app.integration.mural.board import registry as widget_registry
from app.integration.mural.board.renderers import msx as widget_msx
from app.integration.mural.board.summary import renderer as summary_renderer
from tests.fakes import (
    in_memory_board_access_request_store,
    in_memory_oauth_state_store,
    in_memory_token_store,
)


class TestProvider(dishka.Provider):
    """APP-scoped provider that substitutes in-memory fakes for all persistence."""

    scope = dishka.Scope.APP

    @dishka.provide
    def provide_token_store(self) -> token_store.TokenStore:
        return in_memory_token_store.InMemoryTokenStore()

    @dishka.provide
    def provide_board_access_request_store(
        self,
    ) -> approval_ports.BoardAccessRequestStore:
        return in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()

    @dishka.provide
    def provide_board_guard(self) -> guard_module.BoardGuard:
        return guard_module.AllowAllBoardGuard()

    @dishka.provide
    def provide_state_store(self) -> token_store.OAuthStateStore:
        return in_memory_oauth_state_store.InMemoryOAuthStateStore()

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
