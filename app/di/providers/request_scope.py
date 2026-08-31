from collections.abc import AsyncIterator

import dishka
import httpx

from app import config as app_config
from app.common import http_client, request_context
from app.integration.linking import oauth_client
from app.integration.linking import ports as token_store
from app.integration.linking import service as linking_service
from app.integration.mural import guard as guard_module
from app.integration.mural import service as board_service
from app.integration.mural.board.renderers import msx as widget_msx
from app.integration.mural.board.summary import renderer as summary_renderer


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
    def provide_linking_service(
        self,
        oauth: oauth_client.OAuthClient,
        tokens: token_store.TokenStore,
        states: token_store.OAuthStateStore,
    ) -> linking_service.LinkingService:
        return linking_service.LinkingService(oauth=oauth, tokens=tokens, states=states)

    @dishka.provide
    def provide_board_service(
        self,
        config: app_config.AppConfig,
        client: httpx.AsyncClient,
        oauth: oauth_client.OAuthClient,
        renderer: widget_msx.WidgetMsxRenderer,
        sum_renderer: summary_renderer.SummaryMsxRenderer,
        guard: guard_module.BoardGuard,
    ) -> board_service.BoardService:
        return board_service.BoardService(
            config=config,
            client=client,
            oauth=oauth,
            renderer=renderer,
            summary_renderer=sum_renderer,
            guard=guard,
        )
