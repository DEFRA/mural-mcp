import dishka
from pymongo.asynchronous import database

from app import config as app_config
from app.integration.linking import mongo_store
from app.integration.linking import ports as token_store
from app.integration.mural import access_request_service
from app.integration.mural import guard as guard_module
from app.integration.mural import mongo_store as approval_mongo_store
from app.integration.mural import ports as approval_ports
from app.integration.mural.board import registry as widget_registry
from app.integration.mural.board.renderers import msx as widget_msx
from app.integration.mural.board.summary import renderer as summary_renderer


class MuralProvider(dishka.Provider):
    @dishka.provide(scope=dishka.Scope.APP)
    def provide_token_store(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
        config: app_config.AppConfig,
    ) -> token_store.TokenStore:
        return mongo_store.MongoTokenStore(db[config.mural_config.token_collection])

    @dishka.provide(scope=dishka.Scope.APP)
    async def provide_oauth_state_store(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
        config: app_config.AppConfig,
    ) -> token_store.OAuthStateStore:
        store = mongo_store.MongoOAuthStateStore(
            db[config.mural_config.oauth_state_collection]
        )
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
        """The one line an operator changes to turn enforcement on: bind
        AllowListBoardGuard once the admin review workflow has real
        approvals to check against (see RESOURCE_GUARD_MODE)."""
        if config.resource_guard_mode == "allow_list":
            return guard_module.AllowListBoardGuard(store)
        return guard_module.AllowAllBoardGuard()
