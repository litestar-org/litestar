from collections.abc import Generator
from logging import INFO
from typing import TYPE_CHECKING, Annotated, Any

import pytest
import structlog
from structlog.testing import capture_logs

from litestar import Response, get, post
from litestar.config.compression import CompressionConfig
from litestar.connection import Request
from litestar.datastructures import Cookie, UploadFile
from litestar.enums import RequestEncodingType
from litestar.handlers import HTTPRouteHandler
from litestar.middleware.logging import LoggingMiddleware
from litestar.params import Body
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from litestar.testing import create_test_client
from tests.helpers import cleanup_logging_impl

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from pytest import MonkeyPatch

    from litestar.middleware.session.server_side import ServerSideSessionConfig


pytestmark = pytest.mark.usefixtures("reset_httpx_logging")


@pytest.fixture(autouse=True)
def cleanup_logging() -> Generator:
    with cleanup_logging_impl():
        yield


@pytest.fixture
def handler() -> HTTPRouteHandler:
    @get("/")
    def handler_fn() -> Response:
        return Response(
            content={"hello": "world"},
            headers={"token": "123", "regular": "abc"},
            cookies=[Cookie(key="first-cookie", value="abc"), Cookie(key="second-cookie", value="xxx")],
        )

    return handler_fn


def test_logging_middleware_regular_logger(caplog: "LogCaptureFixture", handler: HTTPRouteHandler) -> None:
    with (
        create_test_client(route_handlers=[handler], middleware=[LoggingMiddleware("litestar.test")]) as client,
        caplog.at_level(INFO),
    ):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}
        response = client.get("/", headers={"request-header": "1"})
    assert response.status_code == HTTP_200_OK
    assert len(caplog.messages) == 2

    assert caplog.messages[0] == 'HTTP Request: path=/, method=GET, content_type=["",{}], query={}, path_params={}'


def test_logging_middleware_struct_logger(handler: HTTPRouteHandler) -> None:
    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )
    logger = structlog.getLogger("litestar.test")

    with (
        capture_logs() as cap_logs,
        create_test_client(
            route_handlers=[handler],
            middleware=[
                LoggingMiddleware(
                    logger,
                    log_structured=True,
                    request_log_fields=(
                        "path",
                        "method",
                        "content_type",
                        "headers",
                        "cookies",
                        "query",
                        "path_params",
                    ),
                    response_log_fields=("status_code", "cookies", "headers"),
                )
            ],
        ) as client,
    ):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}
        response = client.get("/", headers={"request-header": "1"})
        assert response.status_code == HTTP_200_OK
        assert len(cap_logs) == 2
        assert cap_logs[0] == {
            "event": "HTTP Request",
            "path": "/",
            "method": "GET",
            "content_type": ("", {}),
            "headers": {
                "host": "testserver.local",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "connection": "keep-alive",
                "user-agent": "testclient",
                "request-header": "1",
                "cookie": "request-cookie=abc",
            },
            "cookies": {"request-cookie": "abc"},
            "query": {},
            "path_params": {},
            "log_level": "info",
        }
        assert cap_logs[1] == {
            "event": "HTTP Response",
            "status_code": 200,
            "cookies": {"first-cookie": "abc", "Path": "/", "SameSite": "lax", "second-cookie": "xxx"},
            "headers": {"token": "123", "regular": "abc", "content-length": "17", "content-type": "application/json"},
            "log_level": "info",
        }


def test_logging_middleware_exclude_pattern(caplog: "LogCaptureFixture", handler: HTTPRouteHandler) -> None:
    @get("/exclude")
    def handler2() -> None:
        return None

    with (
        create_test_client(
            route_handlers=[handler, handler2],
            middleware=[LoggingMiddleware("litestar.test", exclude=["^/exclude"])],
        ) as client,
        caplog.at_level(INFO),
    ):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}

        response = client.get("/exclude")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 0

        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 2


def test_logging_middleware_exclude_opt_key(caplog: "LogCaptureFixture", handler: HTTPRouteHandler) -> None:
    @get("/exclude", skip_logging=True)
    def handler2() -> None:
        return None

    with (
        create_test_client(
            route_handlers=[handler, handler2],
            middleware=[LoggingMiddleware("litestar.test", exclude_opt_key="skip_logging")],
        ) as client,
        caplog.at_level(INFO),
    ):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}

        response = client.get("/exclude")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 0

        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 2


@pytest.mark.parametrize("include", [True, False])
def test_logging_middleware_compressed_response_body(
    include: bool, caplog: "LogCaptureFixture", handler: HTTPRouteHandler
) -> None:
    with (
        create_test_client(
            route_handlers=[handler],
            compression_config=CompressionConfig(backend="gzip", minimum_size=1),
            middleware=[
                LoggingMiddleware(
                    "litestar.test",
                    include_compressed_body=include,
                    response_log_fields=[
                        "body",
                    ],
                )
            ],
        ) as client,
    ):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}
        response = client.get("/", headers={"request-header": "1"})
    assert response.status_code == HTTP_200_OK
    assert len(caplog.messages) == 2
    if include:
        assert "body" in caplog.messages[1]
    else:
        assert "body" not in caplog.messages[1]


def test_logging_middleware_post_body() -> None:
    @post("/")
    def post_handler(data: dict[str, str]) -> dict[str, str]:
        return data

    with create_test_client(
        route_handlers=[post_handler],
        middleware=[
            LoggingMiddleware(
                "litestar.test",
            )
        ],
    ) as client:
        res = client.post("/", json={"foo": "bar"})
        assert res.status_code == 201
        assert res.json() == {"foo": "bar"}


async def test_logging_middleware_post_binary_file_without_structlog(monkeypatch: "MonkeyPatch") -> None:
    # https://github.com/litestar-org/litestar/issues/2529

    @post("/")
    async def post_handler(data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)]) -> str:
        content = await data.read()
        return f"{len(content)} bytes"

    with create_test_client(
        route_handlers=[post_handler],
        middleware=[LoggingMiddleware("litestar.test")],
    ) as client:
        res = client.post("/", files={"foo": b"\xfa\xfb"})
        assert res.status_code == 201
        assert res.text == "2 bytes"


@pytest.mark.parametrize("logger_name", ("litestar", "other"))
def test_logging_messages_are_not_doubled(logger_name: str, caplog: "LogCaptureFixture") -> None:
    # https://github.com/litestar-org/litestar/issues/896

    @get("/")
    async def hello_world_handler() -> dict[str, str]:
        return {"hello": "world"}

    logging_middleware = LoggingMiddleware("litestar.test")

    with (
        create_test_client(
            hello_world_handler,
            middleware=[logging_middleware],
        ) as client,
        caplog.at_level(INFO),
    ):
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 2


def test_logging_middleware_log_fields(caplog: "LogCaptureFixture", handler: HTTPRouteHandler) -> None:
    with (
        create_test_client(
            route_handlers=[handler],
            middleware=[
                LoggingMiddleware("litestar.test", response_log_fields=["status_code"], request_log_fields=["path"])
            ],
        ) as client,
        caplog.at_level(INFO),
    ):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}
        response = client.get("/", headers={"request-header": "1"})
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 2

    assert caplog.messages[0] == "HTTP Request: path=/"
    assert caplog.messages[1] == "HTTP Response: status_code=200"


def test_logging_middleware_with_session_middleware(session_backend_config_memory: "ServerSideSessionConfig") -> None:
    # https://github.com/litestar-org/litestar/issues/1228

    @post("/")
    async def set_session(request: Request) -> None:
        request.set_session({"hello": "world"})

    @get("/")
    async def get_session() -> None:
        pass

    with create_test_client(
        [set_session, get_session],
        middleware=[LoggingMiddleware("litestar.test"), session_backend_config_memory.middleware],
    ) as client:
        response = client.post("/")
        assert response.status_code == HTTP_201_CREATED
        assert "session" in client.cookies
        assert client.cookies["session"] != "*****"
        session_id = client.cookies["session"]

        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert "session" in client.cookies
        assert client.cookies["session"] == session_id


def test_structlog_invalid_request_body_handled() -> None:
    # https://github.com/litestar-org/litestar/issues/3063
    @post("/")
    async def hello_world(data: dict[str, Any]) -> dict[str, Any]:
        return data

    with create_test_client(
        route_handlers=[hello_world],
        middleware=[LoggingMiddleware(structlog.get_logger("litestar.test"))],
    ) as client:
        assert client.post("/", headers={"Content-Type": "application/json"}, content=b'{"a": "b",}').status_code == 400
