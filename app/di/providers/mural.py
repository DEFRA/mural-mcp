import dishka
from pymongo.asynchronous import database

from app.mural.board import registry as widget_registry
from app.mural.board.approval import mongo_store as approval_mongo_store
from app.mural.board.approval import ports as approval_ports
from app.mural.board.renderers import msx as widget_msx
from app.mural.board.summary import renderer as summary_renderer
from app.mural.connectivity import mongo_store, state_store
from app.mural.connectivity import ports as token_store


class MuralProvider(dishka.Provider):
    @dishka.provide(scope=dishka.Scope.APP)
    def provide_token_store(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
    ) -> token_store.TokenStore:
        return mongo_store.MongoTokenStore(db["mural_tokens"])

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_oauth_state_store(self) -> state_store.OAuthStateStore:
        return state_store.OAuthStateStore()

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
    def provide_board_approval_store(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
    ) -> approval_ports.BoardApprovalStore:
        return approval_mongo_store.MongoBoardApprovalStore(db["board_approvals"])
