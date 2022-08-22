import logging
from typing import TYPE_CHECKING, Any, cast

import brotli
import pytest
from starlette.responses import PlainTextResponse

from starlite import get
from starlite.config import CompressionConfig
from starlite.config.compression import BrotliMode, CompressionEncoding
from starlite.datastructures import Stream
from starlite.enums import CompressionBackend
from starlite.middleware.compression.brotli import BrotliMiddleware
from starlite.middleware.compression.gzip import GZipMiddleware
from starlite.testing import create_test_client

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from starlette.types import ASGIApp

    from starlite.middleware.compression.base import CompressionMiddleware


@get(path="/")
def handler() -> PlainTextResponse:
    return PlainTextResponse("_starlite_" * 4000)


@get(path="/no-compression")
def no_compress_handler() -> PlainTextResponse:
    return PlainTextResponse("_starlite_")


async def streaming_iter(content: bytes, count: int) -> Any:
    for _ in range(count):
        yield content


def test_no_compression_backend() -> None:
    try:
        client = create_test_client(route_handlers=[handler])
        unpacked_middleware = []
        cur = client.app.asgi_handler
        while hasattr(cur, "app"):
            unpacked_middleware.append(cur)
            cur = cast("ASGIApp", cur.app)  # type: ignore
        else:
            unpacked_middleware.append(cur)
        for middleware in unpacked_middleware:
            assert not isinstance(middleware, (GZipMiddleware, BrotliMiddleware))
    except Exception as exc:
        assert isinstance(exc, ValueError)
        assert "No compression backend specified" in str(exc)


def test_gzip_middleware_from_enum() -> None:
    client = create_test_client(
        route_handlers=[handler], compression_config=CompressionConfig(backend=CompressionBackend.GZIP)
    )
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast("ASGIApp", cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 2
    gzip_middleware = unpacked_middleware[1].handler  # type: ignore
    assert isinstance(gzip_middleware, GZipMiddleware)
    assert gzip_middleware.minimum_size == 500
    assert gzip_middleware.compresslevel == 9


def test_gzip_middleware_custom_settings() -> None:
    client = create_test_client(
        route_handlers=[handler],
        compression_config=CompressionConfig(backend=CompressionBackend.GZIP, minimum_size=1000, gzip_compress_level=3),
    )
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast("ASGIApp", cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 2
    middleware = cast("CompressionMiddleware", unpacked_middleware[1])
    gzip_middleware = middleware.handler
    assert isinstance(gzip_middleware, GZipMiddleware)
    assert gzip_middleware.minimum_size == 1000
    assert gzip_middleware.compresslevel == 3


def test_gzip_middleware_set_from_string() -> None:
    client = create_test_client(route_handlers=[handler], compression_config=CompressionConfig(backend="gzip"))
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast("ASGIApp", cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 2
    middleware = cast("CompressionMiddleware", unpacked_middleware[1])
    gzip_middleware = middleware.handler
    assert isinstance(gzip_middleware, GZipMiddleware)
    assert gzip_middleware.minimum_size == 500
    assert gzip_middleware.compresslevel == 9


def test_brotli_middleware_from_enum() -> None:
    client = create_test_client(route_handlers=[handler], compression_config=CompressionConfig(backend="brotli"))
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast("ASGIApp", cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 2
    brotli_middleware = unpacked_middleware[1].handler  # type: ignore
    assert isinstance(brotli_middleware, BrotliMiddleware)
    assert brotli_middleware.quality == 5
    assert brotli_middleware.mode == BrotliMiddleware._brotli_mode_to_int(BrotliMode.TEXT)
    assert brotli_middleware.lgwin == 22
    assert brotli_middleware.lgblock == 0


def test_brotli_middleware_from_string() -> None:
    client = create_test_client(
        route_handlers=[handler], compression_config=CompressionConfig(backend=CompressionBackend.BROTLI)
    )
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast("ASGIApp", cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 2
    brotli_middleware = unpacked_middleware[1].handler  # type: ignore
    assert isinstance(brotli_middleware, BrotliMiddleware)
    assert brotli_middleware.quality == 5
    assert brotli_middleware.mode == BrotliMiddleware._brotli_mode_to_int(BrotliMode.TEXT)
    assert brotli_middleware.lgwin == 22
    assert brotli_middleware.lgblock == 0


def test_brotli_encoding_disable_for_unsupported_client() -> None:
    with create_test_client(
        route_handlers=[handler], compression_config=CompressionConfig(backend=CompressionBackend.BROTLI)
    ) as client:
        response = client.request("GET", "/", headers={"accept-encoding": "deflate"})
        assert response.status_code == 200, response.text
        assert response.text == "_starlite_" * 4000
        assert "Content-Encoding" not in response.headers
        assert int(response.headers["Content-Length"]) == 40000


def test_brotli_regular_response() -> None:
    with create_test_client(
        route_handlers=[handler], compression_config=CompressionConfig(backend=CompressionBackend.BROTLI)
    ) as client:
        response = client.request("GET", "/")
        assert response.status_code == 200, response.text
        assert response.text == "_starlite_" * 4000
        assert response.headers["Content-Encoding"] == CompressionEncoding.BROTLI
        assert int(response.headers["Content-Length"]) < 40000


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "iterator",
    [
        streaming_iter(content=b"_starlite_" * 400, count=10),
    ],
)
async def test_brotli_streaming_response(iterator: Any) -> None:
    @get("/streaming-response")
    def streaming_handler() -> Stream:
        return Stream(iterator=iterator)

    with create_test_client(
        route_handlers=[streaming_handler], compression_config=CompressionConfig(backend=CompressionBackend.BROTLI)
    ) as client:
        response = client.request("GET", "/streaming-response")
        assert response.status_code == 200, response.text
        assert response.text == "_starlite_" * 4000
        assert response.headers["Content-Encoding"] == CompressionEncoding.BROTLI
        assert "Content-Length" not in response.headers


def test_brotli_dont_compress_small_responses() -> None:
    with create_test_client(
        route_handlers=[no_compress_handler], compression_config=CompressionConfig(backend=CompressionBackend.BROTLI)
    ) as client:
        response = client.request("GET", "/no-compression")
        assert response.status_code == 200, response.text
        assert response.text == "_starlite_"
        assert "Content-Encoding" not in response.headers
        assert int(response.headers["Content-Length"]) == 10


def test_brotli_gzip_fallback_enabled() -> None:
    with create_test_client(
        route_handlers=[handler], compression_config=CompressionConfig(backend=CompressionBackend.BROTLI)
    ) as client:
        response = client.request("GET", "/", headers={"accept-encoding": "gzip"})
        assert response.status_code == 200, response.text
        assert response.text == "_starlite_" * 4000
        assert response.headers["Content-Encoding"] == CompressionEncoding.GZIP
        assert int(response.headers["Content-Length"]) < 40000


def test_brotli_gzip_fallback_disabled() -> None:
    with create_test_client(
        route_handlers=[handler],
        compression_config=CompressionConfig(backend=CompressionBackend.BROTLI, brotli_gzip_fallback=False),
    ) as client:
        response = client.request("GET", "/", headers={"accept-encoding": "gzip"})
        assert response.status_code == 200, response.text
        assert response.text == "_starlite_" * 4000
        assert "Content-Encoding" not in response.headers
        assert int(response.headers["Content-Length"]) == 40000


def test_brotli_middleware_custom_settings() -> None:
    client = create_test_client(
        route_handlers=[handler],
        compression_config=CompressionConfig(
            backend=CompressionBackend.BROTLI,
            minimum_size=1000,
            brotli_quality=3,
            brotli_mode=BrotliMode.FONT,
            brotli_lgwin=20,
            brotli_lgblock=17,
        ),
    )
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast("ASGIApp", cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 2
    brotli_middleware = unpacked_middleware[1].handler  # type: ignore
    assert isinstance(brotli_middleware, BrotliMiddleware)
    assert brotli_middleware.quality == 3
    assert brotli_middleware.mode == BrotliMiddleware._brotli_mode_to_int(BrotliMode.FONT)
    assert brotli_middleware.lgwin == 20
    assert brotli_middleware.lgblock == 17


def test_brotli_middleware_invalid_mode() -> None:
    try:
        create_test_client(
            route_handlers=[handler],
            compression_config=CompressionConfig(
                backend=CompressionBackend.BROTLI,
                brotli_mode="BINARY",
            ),
        )
    except Exception as exc:
        assert isinstance(exc, ValueError)
        assert "not a valid compression optimization mode" in str(exc)


def test_invalid_compression_middleware() -> None:
    try:
        create_test_client(route_handlers=[handler], compression_config=CompressionConfig(backend="super-zip"))  # type: ignore
    except Exception as exc:
        assert isinstance(exc, ValueError)


@pytest.mark.parametrize(
    "mode, exp",
    [
        (BrotliMode.TEXT, brotli.MODE_TEXT),
        (BrotliMode.FONT, brotli.MODE_FONT),
        (BrotliMode.GENERIC, brotli.MODE_GENERIC),
    ],
)
def test_brotli_middleware_brotli_mode_to_int(mode: BrotliMode, exp: int) -> None:
    assert BrotliMiddleware._brotli_mode_to_int(mode) == exp
