from typing import Any

import httpx

from app import config as app_config
from app.integration.linking import exceptions, oauth_client
from app.integration.mural import guard as guard_module
from app.integration.mural.board import exceptions as board_exceptions
from app.integration.mural.board.renderers import msx as msx_renderer
from app.integration.mural.board.summary import builder as summary_builder
from app.integration.mural.board.summary import renderer as summary_renderer
from app.integration.mural.board.widgets import builder, nodes
from app.integration.mural.board.widgets.strategies import (
    base as strategy_base,
)
from app.integration.mural.board.widgets.strategies import (
    spatial as spatial_strategy,
)


def _widget_text_fields(widget: nodes.AnyWidget) -> list[str]:
    return [
        getattr(widget, "text", None) or "",
        getattr(widget, "html_text", None) or "",
        getattr(widget, "title", None) or "",
    ]


class BoardService:
    """Fetches a Mural board's widgets and renders them as MSX."""

    def __init__(
        self,
        config: app_config.AppConfig,
        client: httpx.AsyncClient,
        oauth: oauth_client.OAuthClient,
        renderer: msx_renderer.WidgetMsxRenderer,
        summary_renderer: summary_renderer.SummaryMsxRenderer,
        guard: guard_module.BoardGuard,
    ) -> None:
        self._config = config
        self._client = client
        self._oauth = oauth
        self._renderer = renderer
        self._summary_renderer = summary_renderer
        self._guard = guard

    async def _load(
        self,
        user_id: str,
        mural_id: str,
        strategy: strategy_base.GroupingStrategy | None = None,
    ) -> tuple[list[nodes.AnyWidget], builder.WidgetTree]:
        await self._guard.check(user_id, mural_id)
        access_token = await self._oauth.get_valid_token(user_id)
        raw = await self._fetch_widgets(mural_id, access_token)
        parsed = nodes.parse_widgets(raw)
        tree = builder.WidgetTree.build(parsed, strategy)
        return parsed, tree

    async def fetch_summary(
        self, user_id: str, mural_id: str, use_spatial_grouping: bool = False
    ) -> str:
        """Return a compact MSX summary of the board's top-level regions."""
        strategy = (
            spatial_strategy.SpatialGroupingStrategy() if use_spatial_grouping else None
        )
        _, tree = await self._load(user_id, mural_id, strategy)
        summary = summary_builder.BoardSummary.build(tree, mural_id)
        return self._summary_renderer.render(summary)

    async def fetch_region(
        self,
        user_id: str,
        mural_id: str,
        region_id: str,
        use_spatial_grouping: bool = False,
    ) -> str:
        """Return full MSX for the widgets within a board region."""
        strategy = (
            spatial_strategy.SpatialGroupingStrategy() if use_spatial_grouping else None
        )
        _, tree = await self._load(user_id, mural_id, strategy)

        try:
            tree.resolve(region_id)
        except KeyError as exc:
            msg = f'Region "{region_id}" not found on board {mural_id}.'
            raise board_exceptions.BoardRegionNotFoundError(msg) from exc

        return self._renderer.render_subtree(tree, region_id)

    async def fetch_connections(
        self, user_id: str, mural_id: str, widget_id: str
    ) -> str:
        """Return all arrows connected to widget_id and their resolved endpoints."""
        parsed, tree = await self._load(user_id, mural_id)
        return self._renderer.render_connections(widget_id, parsed, tree)

    async def search_widgets(
        self,
        user_id: str,
        mural_id: str,
        query: str | None,
        widget_type: str | None,
    ) -> str:
        """Return MSX leaf nodes for widgets matching query and/or type."""
        parsed, tree = await self._load(user_id, mural_id)

        matches: list[nodes.AnyWidget] = []
        needle = query.lower() if query else None

        for widget in parsed:
            if widget_type and widget.type != widget_type:
                continue
            if needle:
                fields = _widget_text_fields(widget)
                if not any(needle in f.lower() for f in fields):
                    continue
            matches.append(widget)

        if not matches:
            return "No widgets matched."

        return self._renderer.render_widgets((w.id for w in matches), tree)

    async def _fetch_widgets(
        self, mural_id: str, access_token: str
    ) -> list[dict[str, Any]]:
        api_base = self._config.mural_config.api_base.rstrip("/")
        base_url = f"{api_base}/public/v1/murals/{mural_id}/widgets"
        url: str | None = base_url
        next_params: dict[str, str] | None = None
        all_widgets: list[dict[str, Any]] = []

        while url:
            try:
                response = await self._client.get(
                    url,
                    params=next_params,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.RequestError as exc:
                raise exceptions.MuralUnavailableError(str(exc)) from exc

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise exceptions.MuralApiError(response.status_code) from exc
            data = response.json()

            page = data.get("value", data) if isinstance(data, dict) else data
            all_widgets.extend(page)

            resolved = self._resolve_next(data, base_url)

            if resolved is None:
                break

            url, next_params = resolved

        return all_widgets

    @staticmethod
    def _resolve_next(
        data: object,
        base_url: str,
    ) -> tuple[str, dict[str, str] | None] | None:
        if not isinstance(data, dict):
            return None

        next_token = data.get("next")

        if not next_token:
            return None

        if next_token.startswith("http"):
            return next_token, None

        return base_url, {"next": next_token}
