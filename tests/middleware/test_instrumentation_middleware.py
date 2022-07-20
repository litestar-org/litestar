import logging
from typing import cast

from opentelemetry.util.http import ExcludeList
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp

from starlite import get
from starlite.config import InstrumentationBackend, InstrumentationConfig
from starlite.middleware.instrumentation.opentelemetry import OpenTelemetryMiddleware
from starlite.testing import create_test_client

logger = logging.getLogger(__name__)


@get(path="/test_path")
def handler() -> PlainTextResponse:
    return PlainTextResponse("_starlite_" * 4000, status_code=200)


def test_invalid_instrumentation_middleware_backend() -> None:

    try:
        create_test_client(route_handlers=[handler], instrumentation_config=InstrumentationConfig(backend="oracle-oem"))
    except Exception as e:
        assert isinstance(e, ValueError)


def test_opentelemetry_backend() -> None:

    client = create_test_client(
        route_handlers=[handler], instrumentation_config=InstrumentationConfig(backend="opentelemetry")
    )
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast(ASGIApp, cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 2
    middleware = unpacked_middleware[1].handler  # type: ignore
    assert isinstance(middleware, OpenTelemetryMiddleware)


def test_opentelemetry_backend_excluded_urls() -> None:

    client = create_test_client(
        route_handlers=[handler],
        instrumentation_config=InstrumentationConfig(
            backend=InstrumentationBackend.OPENTELEMETRY, excluded_urls="/test_path"
        ),
    )
    unpacked_middleware = []
    cur = client.app.asgi_handler
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast(ASGIApp, cur.app)  # type: ignore
    else:
        unpacked_middleware.append(cur)
    assert len(unpacked_middleware) == 2
    middleware = unpacked_middleware[1].handler  # type: ignore
    assert isinstance(middleware, OpenTelemetryMiddleware)
    assert isinstance(middleware.excluded_urls, ExcludeList)

    # assert middleware.excluded_urls == parse_excluded_urls("/test_path")
