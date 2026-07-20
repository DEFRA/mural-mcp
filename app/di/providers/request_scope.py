from collections.abc import AsyncIterator

import dishka
import httpx

from app import config as app_config
from app.common import http_client, request_context
from app.mural.board import service as board_service
from app.mural.board.renderers import msx as widget_msx
from app.mural.board.summary import renderer as summary_renderer
from app.mural.connectivity import oauth_client
from app.mural.connectivity import ports as token_store


class RequestScopeProvider(dishka.Provider):
    """REQUEST-scoped wiring: per-request httpx client plus the services that
    use it (OAuthClient, BoardService). RequestContext arrives via from_context
    — populated by the FastAPI middleware (HTTP) or the dishka_inject
    decorator (MCP)."""

    scope = dishka.Scope.REQUEST

    rc = dishka.from_context(request_context.RequestContext)

    @dishka.provide
    async def provide_httpx_client(
        self,
        config: app_config.AppConfig,
        rc: request_context.RequestContext,
    ) -> AsyncIterator[httpx.AsyncClient]:
        proxy = str(config.http_proxy) if config.http_proxy else None
        async with http_client.create_async_client(
            tracing_header=config.tracing_header,
            trace_id=rc.trace_id,
            proxy=proxy,
        ) as client:
            yield client

    @dishka.provide
    def provide_oauth_client(
        self,
        config: app_config.AppConfig,
        client: httpx.AsyncClient,
        tokens: token_store.TokenStore,
    ) -> oauth_client.OAuthClient:
        return oauth_client.OAuthClient(config=config, client=client, tokens=tokens)

    @dishka.provide
    def provide_board_service(
        self,
        config: app_config.AppConfig,
        client: httpx.AsyncClient,
        oauth: oauth_client.OAuthClient,
        renderer: widget_msx.WidgetMsxRenderer,
        sum_renderer: summary_renderer.SummaryMsxRenderer,
    ) -> board_service.BoardService:
        return board_service.BoardService(
            config=config,
            client=client,
            oauth=oauth,
            renderer=renderer,
            summary_renderer=sum_renderer,
        )
