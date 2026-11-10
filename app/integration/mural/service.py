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
from app.integration.mural.board.rendering import paging
from app.integration.mural.board.rendering import summary as summary_renderer

# Largest page the widgets endpoint accepts (it must be under 100).
_PAGE_LIMIT = "99"

# Widget types the API's `type` filter accepts, by the singular name widgets
# carry. Areas are left out on purpose: an area found by search is rendered
# with its contents, which a type-filtered fetch would not include. Tables
# have no filter at all.
_TYPE_FILTERS = {
    "arrow": "arrows",
    "comment": "comments",
    "file": "files",
    "icon": "icons",
    "image": "images",
    "shape": "shapes",
    "sticky note": "sticky notes",
    "text": "texts",
}

# Nested areas fetched one by one before a full board fetch is cheaper.
_MAX_AREA_FETCHES = 20


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
        access_token = await self._authorise(user_id, mural_id)
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

    async def _authorise(self, user_id: str, mural_id: str) -> str:
        """Check board access, then return the user's Mural token.

        Every public method starts here, before any call to Mural.
        """
        await self._guard.check(user_id, mural_id)
        return await self._oauth.get_valid_token(user_id)

    async def _load(
        self,
        user_id: str,
        mural_id: str,
        strategy: strategy_base.GroupingStrategy | None = None,
    ) -> tuple[list[nodes.AnyWidget], nodes.WidgetTree]:
        access_token = await self._authorise(user_id, mural_id)
        return await self._load_board(mural_id, access_token, strategy)

    async def _load_board(
        self,
        mural_id: str,
        access_token: str,
        strategy: strategy_base.GroupingStrategy | None = None,
    ) -> tuple[list[nodes.AnyWidget], nodes.WidgetTree]:
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
        offset: int = 0,
    ) -> tuple[str, paging.Page]:
        """Return MSX for part of a region, and which part it is."""
        access_token = await self._authorise(user_id, mural_id)
        tree = await self._load_region(
            mural_id, region_id, access_token, use_spatial_grouping
        )
        return self._renderer.render_region_page(tree, region_id, offset=offset)

    async def _load_region(
        self,
        mural_id: str,
        region_id: str,
        access_token: str,
        use_spatial_grouping: bool = False,
    ) -> nodes.WidgetTree:
        """A tree that contains region_id and everything inside it.

        An area is fetched on its own with its descendants; anything else
        (spatial groups, table parts) needs the whole board.

        Raises:
            BoardRegionNotFoundError: if the region is not on the board.
        """
        tree = None
        if not use_spatial_grouping:
            tree = await self._load_area(mural_id, region_id, access_token)

        if tree is None:
            strategy = (
                spatial_strategy.SpatialGroupingStrategy()
                if use_spatial_grouping
                else None
            )
            _, tree = await self._load_board(mural_id, access_token, strategy)

        try:
            tree.resolve(region_id)
        except KeyError as exc:
            msg = f'Region "{region_id}" not found on board {mural_id}.'
            raise board_exceptions.BoardRegionNotFoundError(msg) from exc
        return tree

    async def _load_area(
        self, mural_id: str, area_id: str, access_token: str
    ) -> nodes.WidgetTree | None:
        """Build the tree of one area from targeted fetches.

        Returns None when the region is not an area, or when fetching it piece
        by piece would not be complete or cheaper; the caller then loads the
        whole board.
        """
        try:
            area = await self._fetch_widget(mural_id, area_id, access_token)
        except board_exceptions.WidgetNotFoundError:
            return None
        if not isinstance(area, widget_schemas.AreaWidget):
            return None

        widgets: list[nodes.AnyWidget] = [area]
        pending = [area.id]
        fetches = 0
        while pending:
            if fetches >= _MAX_AREA_FETCHES:
                return None
            parent = pending.pop(0)
            fetches += 1
            raw = await self._fetch_widgets(mural_id, access_token, parent_id=parent)
            children = parser.parse_widgets(raw)
            # A table's cells hang off its rows and columns, not its parent,
            # so the area's own children don't carry them.
            if any(isinstance(c, widget_schemas.TableWidget) for c in children):
                return None
            widgets += children
            pending += [
                c.id for c in children if isinstance(c, widget_schemas.AreaWidget)
            ]

        return parser.build_tree(widgets)

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
        offset: int = 0,
        region_id: str | None = None,
    ) -> tuple[str, paging.Page]:
        """Return MSX for part of the widgets matching query and/or type.

        With region_id, only widgets inside that region are searched. Otherwise
        a type the API can filter on is fetched on its own instead of the
        whole board.
        """
        access_token = await self._authorise(user_id, mural_id)
        type_filter = _TYPE_FILTERS.get(widget_type) if widget_type else None

        if region_id:
            tree = await self._load_region(mural_id, region_id, access_token)
            candidates = tree.shown_descendant_widgets(region_id)
        elif type_filter:
            raw = await self._fetch_widgets(mural_id, access_token, types=[type_filter])
            candidates = parser.parse_widgets(raw)
            tree = parser.build_tree(candidates)
        else:
            candidates, tree = await self._load_board(mural_id, access_token)

        needle = query.lower() if query else None
        matches: list[str] = []

        for widget in candidates:
            if widget_type and widget.type != widget_type:
                continue
            if not nodes.is_shown(widget):
                continue
            if needle:
                fields = _widget_text_fields(widget)
                if not any(needle in f.lower() for f in fields):
                    continue
            matches.append(widget.id)

        if not matches:
            return "No widgets matched.", paging.Page(
                shown=0, total=0, offset=0, next_offset=None
            )

        return self._renderer.render_widgets(matches, tree, offset=offset)

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
        self,
        mural_id: str,
        access_token: str,
        *,
        types: list[str] | None = None,
        parent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch every page of a board's widgets, optionally filtered by the API."""
        base_url = self._widgets_url(mural_id)
        # The API needs the same filters again alongside each `next` token.
        filters = {"limit": _PAGE_LIMIT}
        if types:
            filters["type"] = ",".join(types)
        if parent_id:
            filters["parentId"] = parent_id

        url: str | None = base_url
        params: dict[str, str] | None = filters
        all_widgets: list[dict[str, Any]] = []

        while url:
            data = await self._get_json(url, params, access_token)

            page = data.get("value", data) if isinstance(data, dict) else data
            all_widgets.extend(page)

            resolved = self._resolve_next(data, base_url)

            if resolved is None:
                break

            url, next_params = resolved
            # An absolute next URL already carries everything it needs.
            params = {**filters, **next_params} if next_params is not None else None

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

        payload = (
            data["value"]
            if isinstance(data, dict) and isinstance(data.get("value"), dict)
            else data
        )
        if not isinstance(payload, dict) or "id" not in payload:
            msg = f'Widget "{widget_id}" not found on board {mural_id}.'
            raise board_exceptions.WidgetNotFoundError(msg)
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
