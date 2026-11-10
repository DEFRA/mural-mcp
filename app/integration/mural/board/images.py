"""Fetch, resize and cache a board image for an agent.

Mural gives an image widget a signed, expiring download URL. An agent can't
use that, and the full-size file would waste its context, so the server
downloads the image, shrinks it to a size the model can read, and returns the
bytes. Only the processed result is kept in memory.
"""

import asyncio
import collections
import dataclasses
import io
import urllib.parse
from typing import Literal

import httpx2
from PIL import Image, ImageOps, UnidentifiedImageError

from app.integration.mural.board import errors
from app.integration.mural.board.parsing import schemas

type ImageSize = Literal["preview", "full"]

# Longest edge in pixels. Claude downsamples anything larger than ~1568px, so
# "full" is the most detail an agent can use; "preview" is ~1k tokens.
MAX_EDGE: dict[str, int] = {"preview": 1024, "full": 1568}

_MAX_PIXELS = 50_000_000
_MAX_REDIRECTS = 3
_READABLE_FORMATS = ["PNG", "JPEG", "GIF", "WEBP"]
_JPEG_QUALITY = 80
# At or below this many colours an image is a flat-colour diagram; a greyscale
# photo (up to 256 greys) must not count as one.
_MAX_DIAGRAM_COLOURS = 64


@dataclasses.dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    format: Literal["png", "jpeg"]


class ImageFetcher:
    """Downloads an image from a Mural asset host, within limits.

    The URL is signed, so no credentials are sent. Redirects are followed by
    hand so every hop is checked against the host allow-list.
    """

    def __init__(
        self,
        client: httpx2.AsyncClient,
        allowed_hosts: list[str],
        max_bytes: int,
    ) -> None:
        self._client = client
        self._allowed_hosts = [h.lower().lstrip(".") for h in allowed_hosts]
        self._max_bytes = max_bytes

    def _check_url(self, url: str) -> None:
        parts = urllib.parse.urlsplit(url)
        host = (parts.hostname or "").lower()
        allowed = any(host == h or host.endswith(f".{h}") for h in self._allowed_hosts)
        if parts.scheme != "https" or not allowed:
            msg = f'Images are not served from "{host}".'
            raise errors.ImageHostNotAllowedError(msg)

    async def fetch(self, url: str) -> bytes:
        for _ in range(_MAX_REDIRECTS + 1):
            self._check_url(url)
            try:
                async with self._client.stream("GET", url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location", "")
                        url = urllib.parse.urljoin(url, location)
                        continue
                    return await self._read(response)
            except httpx2.RequestError as exc:
                msg = "The image host could not be reached. Try again."
                raise errors.ImageNotAvailableError(msg) from exc

        msg = "The image link redirected too many times."
        raise errors.ImageNotAvailableError(msg)

    async def _read(self, response: httpx2.Response) -> bytes:
        if response.status_code != httpx2.codes.OK:
            msg = (
                "The image could not be downloaded "
                f"(status {response.status_code}); its link may have expired."
            )
            raise errors.ImageNotAvailableError(msg)

        content_type = response.headers.get("content-type", "")
        if not content_type.lower().startswith("image/"):
            msg = "The image format is not supported."
            raise errors.UnsupportedImageError(msg)

        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            raise errors.ImageTooLargeError(_TOO_LARGE)

        body = bytearray()
        async for chunk in response.aiter_bytes():
            body += chunk
            if len(body) > self._max_bytes:
                raise errors.ImageTooLargeError(_TOO_LARGE)
        return bytes(body)


_TOO_LARGE = "The image is too large to load."


def _has_transparency(img: Image.Image) -> bool:
    return img.mode in {"RGBA", "LA"} or "transparency" in img.info


def _crop_to_mask(img: Image.Image, mask: schemas.ImageMask | None) -> Image.Image:
    """Crop to the window the board shows. The mask is in natural-image pixels."""
    if mask is None:
        return img
    left = max(0, round(mask.left))
    top = max(0, round(mask.top))
    right = min(img.width, round(mask.left + mask.width))
    bottom = min(img.height, round(mask.top + mask.height))
    if right <= left or bottom <= top:
        return img
    return img.crop((left, top, right, bottom))


def process_image(
    raw: bytes, *, max_edge: int, mask: schemas.ImageMask | None = None
) -> ProcessedImage:
    """Crop, shrink and re-encode an image.

    Diagrams and screenshots (transparency, or few colours) stay lossless PNG;
    everything else becomes JPEG.

    Raises:
        ImageTooLargeError: if the image has too many pixels to decode safely.
        UnsupportedImageError: if the bytes are not a readable image.
    """
    try:
        img: Image.Image = Image.open(io.BytesIO(raw), formats=_READABLE_FORMATS)
        if img.width * img.height > _MAX_PIXELS:
            raise errors.ImageTooLargeError(_TOO_LARGE)  # noqa: TRY301
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        msg = "The image format is not supported."
        raise errors.UnsupportedImageError(msg) from exc

    img = ImageOps.exif_transpose(img)
    img = _crop_to_mask(img, mask)
    img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    if (
        _has_transparency(img)
        or img.mode == "P"
        or img.getcolors(_MAX_DIAGRAM_COLOURS) is not None
    ):
        img.save(out, format="PNG", optimize=True)
        return ProcessedImage(out.getvalue(), "png")

    img.convert("RGB").save(out, format="JPEG", quality=_JPEG_QUALITY)
    return ProcessedImage(out.getvalue(), "jpeg")


type CacheKey = tuple[object, ...]


class ProcessedImageCache:
    """In-memory LRU of processed images, bounded by total bytes.

    Keys carry the widget's edit timestamps, so an edited image misses the
    cache on its own and nothing needs invalidating.
    """

    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes
        self._size = 0
        self._items: collections.OrderedDict[CacheKey, ProcessedImage] = (
            collections.OrderedDict()
        )

    def get(self, key: CacheKey) -> ProcessedImage | None:
        item = self._items.get(key)
        if item is not None:
            self._items.move_to_end(key)
        return item

    def put(self, key: CacheKey, image: ProcessedImage) -> None:
        if len(image.data) > self._max_bytes:
            return
        previous = self._items.pop(key, None)
        if previous is not None:
            self._size -= len(previous.data)
        self._items[key] = image
        self._size += len(image.data)
        while self._size > self._max_bytes:
            _, evicted = self._items.popitem(last=False)
            self._size -= len(evicted.data)


class ImageLoader:
    """Download, process and cache one image."""

    def __init__(self, fetcher: ImageFetcher, cache: ProcessedImageCache) -> None:
        self._fetcher = fetcher
        self._cache = cache

    async def load(
        self,
        *,
        key: CacheKey,
        url: str,
        size: ImageSize,
        mask: schemas.ImageMask | None,
    ) -> ProcessedImage:
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        raw = await self._fetcher.fetch(url)
        # Decoding is CPU-bound; keep it off the event loop.
        processed = await asyncio.to_thread(
            process_image, raw, max_edge=MAX_EDGE[size], mask=mask
        )
        self._cache.put(key, processed)
        return processed
