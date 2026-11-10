import io

import httpx2
import pytest
from PIL import Image

from app.integration.mural.board import errors, images
from app.integration.mural.board.parsing import schemas
from tests.fakes import httpx_helpers


def _png(size=(400, 200), mode="RGB", color=(10, 20, 30)) -> bytes:
    out = io.BytesIO()
    Image.new(mode, size, color).save(out, format="PNG")
    return out.getvalue()


def _photo(size=(300, 300)) -> bytes:
    """Many colours, so it is not mistaken for a diagram."""
    img = Image.merge("RGB", [Image.effect_noise(size, 80) for _ in range(3)])
    out = io.BytesIO()
    img.save(out, format="JPEG")
    return out.getvalue()


def _open(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


class TestProcessImage:
    def test_shrinks_to_the_longest_edge_keeping_aspect_ratio(self) -> None:
        result = images.process_image(_png((2000, 1000)), max_edge=1000)
        assert _open(result.data).size == (1000, 500)

    def test_never_enlarges_a_small_image(self) -> None:
        result = images.process_image(_png((100, 50)), max_edge=1000)
        assert _open(result.data).size == (100, 50)

    def test_flat_colour_diagrams_stay_png(self) -> None:
        assert images.process_image(_png(), max_edge=1000).format == "png"

    def test_transparency_stays_png(self) -> None:
        raw = _png(mode="RGBA", color=(1, 2, 3, 0))
        assert images.process_image(raw, max_edge=1000).format == "png"

    def test_greyscale_photos_become_jpeg_not_png(self) -> None:
        out = io.BytesIO()
        Image.effect_noise((300, 300), 80).save(out, format="PNG")
        assert images.process_image(out.getvalue(), max_edge=1000).format == "jpeg"

    def test_photos_become_jpeg(self) -> None:
        result = images.process_image(_photo(), max_edge=1000)
        assert result.format == "jpeg"
        assert _open(result.data).format == "JPEG"

    def test_crops_to_the_mask_before_resizing(self) -> None:
        mask = schemas.ImageMask(top=0, left=100, width=200, height=200)
        result = images.process_image(_png((400, 200)), max_edge=1000, mask=mask)
        assert _open(result.data).size == (200, 200)

    def test_a_mask_outside_the_image_is_clamped(self) -> None:
        mask = schemas.ImageMask(top=0, left=300, width=500, height=500)
        result = images.process_image(_png((400, 200)), max_edge=1000, mask=mask)
        assert _open(result.data).size == (100, 200)

    def test_a_mask_with_nothing_in_it_is_ignored(self) -> None:
        mask = schemas.ImageMask(top=0, left=900, width=10, height=10)
        result = images.process_image(_png((400, 200)), max_edge=1000, mask=mask)
        assert _open(result.data).size == (400, 200)

    def test_rejects_bytes_that_are_not_an_image(self) -> None:
        with pytest.raises(errors.UnsupportedImageError):
            images.process_image(b"not an image", max_edge=1000)

    def test_rejects_an_image_with_too_many_pixels(self, monkeypatch) -> None:
        monkeypatch.setattr(images, "_MAX_PIXELS", 100)
        with pytest.raises(errors.ImageTooLargeError):
            images.process_image(_png((200, 200)), max_edge=1000)


def _fetcher(responses, *, max_bytes=1_000_000, hosts=("example.com",)):
    client, transport = httpx_helpers.make_mock_client(responses)
    return images.ImageFetcher(client, list(hosts), max_bytes), transport


def _image_response(body: bytes = b"x", **kw) -> httpx2.Response:
    headers = {"content-type": "image/png", **kw.pop("headers", {})}
    return httpx2.Response(200, content=body, headers=headers, **kw)


class TestImageFetcher:
    async def test_downloads_from_an_allowed_host(self) -> None:
        fetcher, _ = _fetcher([_image_response(b"abc")])
        assert await fetcher.fetch("https://assets.example.com/a.png?sig=1") == b"abc"

    async def test_sends_no_credentials(self) -> None:
        fetcher, transport = _fetcher([_image_response()])
        await fetcher.fetch("https://assets.example.com/a.png")
        assert "authorization" not in transport.requests[0].headers

    async def test_refuses_another_host_without_calling_it(self) -> None:
        fetcher, transport = _fetcher([])
        with pytest.raises(errors.ImageHostNotAllowedError, match="evil.test"):
            await fetcher.fetch("https://evil.test/a.png")
        assert transport.requests == []

    async def test_a_lookalike_host_is_not_a_subdomain(self) -> None:
        fetcher, _ = _fetcher([])
        with pytest.raises(errors.ImageHostNotAllowedError):
            await fetcher.fetch("https://notexample.com/a.png")

    async def test_refuses_plain_http(self) -> None:
        fetcher, _ = _fetcher([])
        with pytest.raises(errors.ImageHostNotAllowedError):
            await fetcher.fetch("http://assets.example.com/a.png")

    async def test_follows_a_redirect_to_an_allowed_host(self) -> None:
        redirect = httpx2.Response(
            302, headers={"location": "https://cdn.example.com/b"}
        )
        fetcher, transport = _fetcher([redirect, _image_response(b"ok")])
        assert await fetcher.fetch("https://assets.example.com/a") == b"ok"
        assert str(transport.requests[1].url) == "https://cdn.example.com/b"

    async def test_refuses_a_redirect_to_another_host(self) -> None:
        redirect = httpx2.Response(302, headers={"location": "https://evil.test/b"})
        fetcher, transport = _fetcher([redirect])
        with pytest.raises(errors.ImageHostNotAllowedError):
            await fetcher.fetch("https://assets.example.com/a")
        assert len(transport.requests) == 1

    async def test_gives_up_on_a_redirect_loop(self) -> None:
        loop = httpx2.Response(
            302, headers={"location": "https://assets.example.com/a"}
        )
        fetcher, _ = _fetcher([loop] * 10)
        with pytest.raises(errors.ImageNotAvailableError):
            await fetcher.fetch("https://assets.example.com/a")

    async def test_aborts_a_body_over_the_limit(self) -> None:
        fetcher, _ = _fetcher([_image_response(b"x" * 100)], max_bytes=10)
        with pytest.raises(errors.ImageTooLargeError):
            await fetcher.fetch("https://assets.example.com/a")

    async def test_refuses_a_declared_size_over_the_limit(self) -> None:
        response = _image_response(b"x", headers={"content-length": "999"})
        fetcher, _ = _fetcher([response], max_bytes=10)
        with pytest.raises(errors.ImageTooLargeError):
            await fetcher.fetch("https://assets.example.com/a")

    async def test_refuses_a_response_that_is_not_an_image(self) -> None:
        response = httpx2.Response(
            200, content=b"<html>", headers={"content-type": "text/html"}
        )
        fetcher, _ = _fetcher([response])
        with pytest.raises(errors.UnsupportedImageError):
            await fetcher.fetch("https://assets.example.com/a")

    @pytest.mark.parametrize("status", [403, 404, 500])
    async def test_an_error_status_is_reported_without_the_url(self, status) -> None:
        fetcher, _ = _fetcher([httpx2.Response(status)])
        with pytest.raises(errors.ImageNotAvailableError) as exc:
            await fetcher.fetch("https://assets.example.com/a?sig=secret")
        assert "secret" not in str(exc.value)
        assert str(status) in str(exc.value)

    async def test_an_unreachable_host_is_not_available(self) -> None:
        fetcher, _ = _fetcher([httpx2.ConnectError("boom")])
        with pytest.raises(errors.ImageNotAvailableError):
            await fetcher.fetch("https://assets.example.com/a")


def _img(n: int) -> images.ProcessedImage:
    return images.ProcessedImage(b"x" * n, "png")


class TestProcessedImageCache:
    def test_returns_what_was_stored(self) -> None:
        cache = images.ProcessedImageCache(100)
        cache.put(("a",), _img(10))
        assert cache.get(("a",)) == _img(10)
        assert cache.get(("b",)) is None

    def test_evicts_the_least_recently_used_over_the_byte_limit(self) -> None:
        cache = images.ProcessedImageCache(25)
        cache.put(("a",), _img(10))
        cache.put(("b",), _img(10))
        cache.get(("a",))
        cache.put(("c",), _img(10))
        assert cache.get(("b",)) is None
        assert cache.get(("a",)) is not None
        assert cache.get(("c",)) is not None

    def test_replacing_a_key_does_not_double_count_it(self) -> None:
        cache = images.ProcessedImageCache(25)
        cache.put(("a",), _img(20))
        cache.put(("a",), _img(20))
        cache.put(("b",), _img(5))
        assert cache.get(("a",)) is not None

    def test_an_image_bigger_than_the_cache_is_not_stored(self) -> None:
        cache = images.ProcessedImageCache(5)
        cache.put(("a",), _img(10))
        assert cache.get(("a",)) is None


class TestImageLoader:
    async def test_second_load_of_the_same_key_skips_the_download(self) -> None:
        fetcher, transport = _fetcher([_image_response(_png())])
        loader = images.ImageLoader(fetcher, images.ProcessedImageCache(1_000_000))

        kwargs = {
            "key": ("m", "w", 1, 1, "preview"),
            "url": "https://a.example.com/x",
            "size": "preview",
            "mask": None,
        }
        first = await loader.load(**kwargs)
        second = await loader.load(**kwargs)

        assert first == second
        assert len(transport.requests) == 1

    async def test_an_edited_widget_is_downloaded_again(self) -> None:
        fetcher, transport = _fetcher(
            [_image_response(_png()), _image_response(_png())]
        )
        loader = images.ImageLoader(fetcher, images.ProcessedImageCache(1_000_000))

        for edited_on in (1, 2):
            await loader.load(
                key=("m", "w", edited_on, edited_on, "preview"),
                url="https://a.example.com/x",
                size="preview",
                mask=None,
            )

        assert len(transport.requests) == 2

    async def test_full_is_larger_than_preview(self) -> None:
        fetcher, _ = _fetcher([_image_response(_png((3000, 1500)))] * 2)
        loader = images.ImageLoader(fetcher, images.ProcessedImageCache(10_000_000))

        sizes = {}
        for size in ("preview", "full"):
            result = await loader.load(
                key=(size,), url="https://a.example.com/x", size=size, mask=None
            )
            sizes[size] = _open(result.data).width

        assert sizes == {"preview": 1024, "full": 1568}
