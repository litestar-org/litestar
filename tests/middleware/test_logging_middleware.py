from logging import INFO
from typing import TYPE_CHECKING

import pytest
from structlog.testing import capture_logs

from starlite import Cookie, LoggingConfig, Response, StructLoggingConfig, get
from starlite.config.compression import CompressionConfig
from starlite.config.logging import default_handlers
from starlite.middleware import LoggingMiddlewareConfig
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


@get("/")
def handler() -> Response:
    return Response(
        content={"hello": "world"},
        headers={"token": "123", "regular": "abc"},
        cookies=[Cookie(key="first-cookie", value="abc"), Cookie(key="second-cookie", value="xxx")],
    )


# due to the limitations of caplog we have to place this call here.
get_logger = LoggingConfig(handlers=default_handlers).configure()


def test_logging_middleware_regular_logger(caplog: "LogCaptureFixture") -> None:
    with create_test_client(
        route_handlers=[handler], middleware=[LoggingMiddlewareConfig().middleware]
    ) as client, caplog.at_level(INFO):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}  # type: ignore
        client.app.get_logger = get_logger
        response = client.get("/", headers={"request-header": "1"})
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 2

        assert (
            caplog.messages[0] == 'HTTP Request: path=/, method=GET, content_type=["",{}], '
            'headers={"host":"testserver.local","accept":"*/*","accept-encoding":"gzip, '
            'deflate, br","connection":"keep-alive","user-agent":"testclient",'
            '"request-header":"1","cookie":"request-cookie=abc"}, '
            'cookies={"request-cookie":"abc"}, query={}, path_params={}, body=None'
        )
        assert (
            caplog.messages[1] == 'HTTP Response: status_code=200, cookies={"first-cookie":"abc","Path":"/","SameSite":'
            '"lax","second-cookie":"xxx"}, headers={"token":"123","regular":"abc","content-type":'
            '"application/json","content-length":"17"}, body={"hello":"world"}'
        )


def test_logging_middleware_struct_logger() -> None:
    with create_test_client(
        route_handlers=[handler],
        middleware=[LoggingMiddlewareConfig().middleware],
        logging_config=StructLoggingConfig(),
    ) as client, capture_logs() as cap_logs:
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}  # type: ignore
        response = client.get("/", headers={"request-header": "1"})
        assert response.status_code == HTTP_200_OK
        assert len(cap_logs) == 2
        assert cap_logs[0] == {
            "path": "/",
            "method": "GET",
            "body": None,
            "content_type": ("", {}),
            "headers": {
                "host": "testserver.local",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br",
                "connection": "keep-alive",
                "user-agent": "testclient",
                "request-header": "1",
                "cookie": "request-cookie=abc",
            },
            "cookies": {"request-cookie": "abc"},
            "query": {},
            "path_params": {},
            "event": "HTTP Request",
            "log_level": "info",
        }
        assert cap_logs[1] == {
            "status_code": 200,
            "cookies": {"first-cookie": "abc", "Path": "/", "SameSite": "lax", "second-cookie": "xxx"},
            "headers": {"token": "123", "regular": "abc", "content-length": "17", "content-type": "application/json"},
            "body": '{"hello":"world"}',
            "event": "HTTP Response",
            "log_level": "info",
        }


def test_logging_middleware_exclude_pattern(caplog: "LogCaptureFixture") -> None:
    @get("/exclude")
    def handler2() -> None:
        return None

    config = LoggingMiddlewareConfig(exclude=["^/exclude"])
    with create_test_client(
        route_handlers=[handler, handler2], middleware=[config.middleware]
    ) as client, caplog.at_level(INFO):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}  # type: ignore
        client.app.get_logger = get_logger

        response = client.get("/exclude")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 0

        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 2


def test_logging_middleware_exclude_opt_key(caplog: "LogCaptureFixture") -> None:
    @get("/exclude", skip_logging=True)
    def handler2() -> None:
        return None

    config = LoggingMiddlewareConfig(exclude_opt_key="skip_logging")
    with create_test_client(
        route_handlers=[handler, handler2], middleware=[config.middleware]
    ) as client, caplog.at_level(INFO):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}  # type: ignore
        client.app.get_logger = get_logger

        response = client.get("/exclude")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 0

        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 2


@pytest.mark.parametrize("include", [True, False])
def test_logging_middleware_compressed_response_body(include: bool, caplog: "LogCaptureFixture") -> None:
    with create_test_client(
        route_handlers=[handler],
        compression_config=CompressionConfig(backend="gzip", minimum_size=1),
        middleware=[LoggingMiddlewareConfig(include_compressed_body=include).middleware],
    ) as client, caplog.at_level(INFO):
        # Set cookies on the client to avoid warnings about per-request cookies.
        client.cookies = {"request-cookie": "abc"}  # type: ignore
        client.app.get_logger = get_logger
        response = client.get("/", headers={"request-header": "1"})
        assert response.status_code == HTTP_200_OK
        assert len(caplog.messages) == 2
        if include:
            assert "body=" in caplog.messages[1]
        else:
            assert "body=" not in caplog.messages[1]
