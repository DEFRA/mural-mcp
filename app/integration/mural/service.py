from typing import Any

import httpx2

from app import config as app_config
from app.integration.linking import exceptions, oauth_client
from app.integration.mural import guard as guard_module
from app.integration.mural.board import errors as board_exceptions
from app.integration.mural.board import images as images_module
from app.integration.mural.board.parsing import grouping as strategy_base
from app.integration.mural.board.parsing import models as nodes
from app.integration.mural.board.parsing import parser
from app.integration.mural.board.parsing import schemas as widget_schemas
from app.integration.mural.board.parsing import spatial as spatial_strategy
from app.integration.mural.board.parsing import summary as summary_builder
from app.integration.mural.board.rendering import msx as msx_renderer
from app.integration.mural.board.rendering import summary as summary_renderer


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
        client: httpx2.AsyncClient,
        oauth: oauth_client.OAuthClient,
        renderer: msx_renderer.WidgetMsxRenderer,
        summary_renderer: summary_renderer.SummaryMsxRenderer,
        guard: guard_module.BoardGuard,
        images: images_module.ImageLoader,
    ) -> None:
        self._config = config
        self._client = client
        self._oauth = oauth
        self._renderer = renderer
        self._summary_renderer = summary_renderer
        self._guard = guard
        self._images = images

    async def fetch_image(
        self,
        user_id: str,
        mural_id: str,
        widget_id: str,
        size: images_module.ImageSize,
    ) -> tuple[str, images_module.ProcessedImage]:
        """Return an MSX label and the processed bytes for an image widget.

        Fetches just this widget, so the signed URL it carries is fresh.
        """
        await self._guard.check(user_id, mural_id)
        access_token = await self._oauth.get_valid_token(user_id)
        widget = await self._fetch_widget(mural_id, widget_id, access_token)

        url, mask = self._image_source(widget)
        key = (
            mural_id,
            widget.id,
            widget.updated_on,
            widget.content_edited_on,
            size,
        )
        processed = await self._images.load(key=key, url=url, size=size, mask=mask)
        return self._renderer.render_widget(widget), processed

    @staticmethod
    def _image_source(
        widget: nodes.AnyWidget,
    ) -> tuple[str, widget_schemas.ImageMask | None]:
        """Pick the URL to download, refusing what the board restricts."""
        if isinstance(widget, widget_schemas.ImageWidget):
            url, mask = widget.url, widget.mask
        elif isinstance(widget, widget_schemas.FileWidget):
            # A file's own url is the file itself; null means downloads are
            # restricted, in which case its preview is withheld too.
            url = widget.preview_url if widget.url else None
            mask = None
            if widget.url and not widget.preview_url:
                msg = f'File "{widget.id}" has no preview to show.'
                raise board_exceptions.ImageNotAvailableError(msg)
        else:
            msg = f'Widget "{widget.id}" is not an image or a file with a preview.'
            raise board_exceptions.WidgetNotAnImageError(msg)

        if not url:
            msg = "Image downloads are restricted on this board."
            raise board_exceptions.ImageRestrictedError(msg)
        return url, mask

    async def _load(
        self,
        user_id: str,
        mural_id: str,
        strategy: strategy_base.GroupingStrategy | None = None,
    ) -> tuple[list[nodes.AnyWidget], nodes.WidgetTree]:
        await self._guard.check(user_id, mural_id)
        access_token = await self._oauth.get_valid_token(user_id)
        raw = await self._fetch_widgets(mural_id, access_token)
        return parser.parse_board(raw, strategy)

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

    def _widgets_url(self, mural_id: str) -> str:
        api_base = self._config.mural_config.api_base.rstrip("/")
        return f"{api_base}/public/v1/murals/{mural_id}/widgets"

    async def _get_json(
        self, url: str, params: dict[str, str] | None, access_token: str
    ) -> Any:
        try:
            response = await self._client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx2.RequestError as exc:
            raise exceptions.MuralUnavailableError(str(exc)) from exc

        try:
            response.raise_for_status()
        except httpx2.HTTPStatusError as exc:
            raise exceptions.MuralApiError(response.status_code) from exc
        return response.json()

    async def _fetch_widgets(
        self, mural_id: str, access_token: str
    ) -> list[dict[str, Any]]:
        base_url = self._widgets_url(mural_id)
        url: str | None = base_url
        next_params: dict[str, str] | None = None
        all_widgets: list[dict[str, Any]] = []

        while url:
            data = await self._get_json(url, next_params, access_token)

            page = data.get("value", data) if isinstance(data, dict) else data
            all_widgets.extend(page)

            resolved = self._resolve_next(data, base_url)

            if resolved is None:
                break

            url, next_params = resolved

        return all_widgets

    async def _fetch_widget(
        self, mural_id: str, widget_id: str, access_token: str
    ) -> nodes.AnyWidget:
        url = f"{self._widgets_url(mural_id)}/{widget_id}"
        try:
            data = await self._get_json(url, None, access_token)
        except exceptions.MuralApiError as exc:
            if exc.status_code == httpx2.codes.NOT_FOUND:
                msg = f'Widget "{widget_id}" not found on board {mural_id}.'
                raise board_exceptions.WidgetNotFoundError(msg) from exc
            raise

        payload = data["value"] if isinstance(data.get("value"), dict) else data
        return parser.parse_widgets([payload])[0]

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
