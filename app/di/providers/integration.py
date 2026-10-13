import dishka
from pymongo.asynchronous import database

from app import config as app_config
from app.integration.linking import mongo_store
from app.integration.linking import ports as token_store
from app.integration.mural import access_request_service
from app.integration.mural import guard as guard_module
from app.integration.mural import mongo_store as approval_mongo_store
from app.integration.mural import ports as approval_ports
from app.integration.mural.board.rendering import msx as widget_msx
from app.integration.mural.board.rendering import registry as widget_registry
from app.integration.mural.board.rendering import summary as summary_renderer


class MuralProvider(dishka.Provider):
    @dishka.provide(scope=dishka.Scope.APP)
    def provide_token_store(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
    ) -> token_store.TokenStore:
        return mongo_store.MongoTokenStore(db["mural_tokens"])

    @dishka.provide(scope=dishka.Scope.APP)
    async def provide_oauth_state_store(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
    ) -> token_store.OAuthStateStore:
        store = mongo_store.MongoOAuthStateStore(db["oauth_states"])
        await store.ensure_indexes()
        return store

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_widget_renderer_registry(
        self,
    ) -> widget_registry.WidgetRendererRegistry:
        return widget_registry.build_default_registry()

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_msx_renderer(
        self,
        reg: widget_registry.WidgetRendererRegistry,
    ) -> widget_msx.WidgetMsxRenderer:
        return widget_msx.WidgetMsxRenderer(reg)

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_summary_msx_renderer(
        self,
        reg: widget_registry.WidgetRendererRegistry,
    ) -> summary_renderer.SummaryMsxRenderer:
        return summary_renderer.SummaryMsxRenderer(reg)

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_board_access_request_store(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
    ) -> approval_ports.BoardAccessRequestStore:
        return approval_mongo_store.MongoBoardAccessRequestStore(db["access_requests"])

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_access_request_service(
        self, store: approval_ports.BoardAccessRequestStore
    ) -> access_request_service.BoardAccessRequestService:
        return access_request_service.BoardAccessRequestService(store)

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_board_guard(
        self,
        config: app_config.AppConfig,
        store: approval_ports.BoardAccessRequestStore,
    ) -> guard_module.BoardGuard:
        """ALLOWED_BOARD_IDS is always the baseline. With
        SELF_SERVICE_ACCESS_ENABLED, an approved access request also grants
        the board."""
        env_guard = guard_module.EnvAllowListBoardGuard(config.allowed_board_ids)
        if config.self_service_access_enabled:
            return guard_module.AnyOfBoardGuard(
                env_guard, guard_module.ApprovedRequestBoardGuard(store)
            )
        return env_guard
