import inspect
from collections.abc import Mapping
from dataclasses import fields
from typing import Any, Literal, Optional, Union, cast

import pytest

from litestar import get
from litestar.config.cors import CORSConfig
from litestar.middleware._internal.cors import CORSMiddleware
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client
from litestar.types.asgi_types import Method


def test_cors_config_defaults() -> None:
    cors_config = CORSConfig()
    assert cors_config.allow_credentials is False
    assert cors_config.allow_headers == ["*"]
    assert cors_config.allow_methods == ["*"]
    assert cors_config.allow_origins == ["*"]
    assert cors_config.allow_origin_regex is None
    assert cors_config.max_age == 600
    assert cors_config.expose_headers == []


def test_cors_middleware_defaults_match_cors_config_defaults() -> None:
    config = CORSConfig()
    middleware = CORSMiddleware()
    config_field_names = {field.name for field in fields(CORSConfig)}

    assert set(inspect.signature(CORSMiddleware.__init__).parameters) - {"self"} == config_field_names
    for name in config_field_names:
        assert getattr(middleware, name) == getattr(config, name), name


def test_cors_max_age_reaches_the_preflight_response() -> None:
    @get("/")
    async def handler() -> None:
        return None

    with create_test_client([handler], cors_config=CORSConfig(max_age=1234)) as client:
        response = client.options(
            "/",
            headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"},
        )
        assert response.headers["Access-Control-Max-Age"] == "1234"


@pytest.mark.parametrize("origin", [None, "http://www.example.com", "https://moishe.zuchmir.com"])
@pytest.mark.parametrize("allow_origins", ["*", "http://www.example.com", "https://moishe.zuchmir.com"])
@pytest.mark.parametrize("allow_credentials", [True, False])
@pytest.mark.parametrize(
    "expose_headers", [["x-first-header", "x-second-header", "x-third-header"], ["*"], ["x-first-header"]]
)
@pytest.mark.parametrize(
    "allow_headers", [["x-first-header", "x-second-header", "x-third-header"], ["*"], ["x-first-header"]]
)
@pytest.mark.parametrize("allow_methods", [["GET", "POST", "PUT", "DELETE"], ["GET", "POST"], ["GET"]])
def test_cors_simple_response(
    origin: Optional[str],
    allow_origins: list[str],
    allow_credentials: bool,
    expose_headers: list[str],
    allow_headers: list[str],
    allow_methods: list[Union[Literal["*"], "Method"]],
) -> None:
    @get("/")
    def handler() -> dict[str, str]:
        return {"hello": "world"}

    cors_config = CORSConfig(
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        expose_headers=expose_headers,
        allow_headers=allow_headers,
        allow_methods=allow_methods,
    )

    with create_test_client(handler, cors_config=cors_config) as client:
        headers: Mapping[str, str] = {"Origin": origin} if origin else {}
        response = client.get("/", headers=headers)
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"hello": "world"}
        assert cors_config.expose_headers == expose_headers
        assert cors_config.allow_origins == allow_origins
        assert cors_config.allow_credentials == allow_credentials
        assert cors_config.allow_headers == allow_headers
        assert cors_config.allow_methods == allow_methods

        if origin:
            if cors_config.is_allow_all_origins:
                assert response.headers.get("Access-Control-Allow-Origin") == "*"
            if cors_config.allow_credentials:
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
            if cors_config.expose_headers:
                assert response.headers.get("Access-Control-Expose-Headers") == ", ".join(
                    sorted(set(cors_config.expose_headers))
                )
            if cors_config.allow_headers:
                assert response.headers.get("Access-Control-Allow-Headers") == ", ".join(
                    sorted(set(cors_config.allow_headers))
                )
            if cors_config.allow_methods:
                assert response.headers.get("Access-Control-Allow-Methods") == ", ".join(
                    sorted(set(cors_config.allow_methods))
                )
        else:
            assert "Access-Control-Allow-Origin" not in response.headers
            assert "Access-Control-Allow-Credentials" not in response.headers
            assert "Access-Control-Expose-Headers" not in response.headers
            assert "Access-Control-Allow-Headers" not in response.headers
            assert "Access-Control-Allow-Methods" not in response.headers


@pytest.mark.parametrize("origin, should_apply_cors", (("http://www.example.com", True), (None, False)))
def test_cors_applied_on_exception_response_if_origin_is_present(
    origin: Optional[str], should_apply_cors: bool
) -> None:
    @get("/")
    def handler() -> dict[str, str]:
        return {"hello": "world"}

    cors_config = CORSConfig(allow_origins=["http://www.example.com"])

    with create_test_client(handler, cors_config=cors_config) as client:
        headers: Mapping[str, str] = {"Origin": origin} if origin else {}
        response = client.get("/abc", headers=headers)
        assert response.status_code == HTTP_404_NOT_FOUND
        if should_apply_cors:
            assert response.headers.get("Access-Control-Allow-Origin") == origin
        else:
            assert not response.headers.get("Access-Control-Allow-Origin")


@pytest.mark.parametrize(
    "allow_origin,origin,host,should_allow",
    [
        ("httpx://good.example", "https://goodXexample", "example.com", False),
        ("https://*good.example", "https://very.good.example", "very.good.example", True),
        ("https://*good.example", "https://verygood.example", "vergood.example", True),
        ("https://*good.example", "https://good.example", "good.example", True),
        ("https://*good.example", "https://bad.example", "bad.example", False),
        ("https://*.good.example", "https://very.good.example", "very.good.example", True),
        ("https://*.good.example", "https://verygood.example", "verygood.example", False),
        ("https://*.good.example", "https://some.verygood.example", "verygood.example", False),
        ("https://*.good.example", "https://good.example", "good.example", False),
    ],
)
def test_cors_test_regex_escape(allow_origin: str, origin: str, host: str, should_allow: bool) -> None:
    @get("/")
    async def handler() -> None:
        return None

    with create_test_client(
        [handler],
        cors_config=CORSConfig(
            allow_origins=[allow_origin],
            allow_credentials=True,
        ),
    ) as client:
        res = client.get("/", headers={"Origin": origin, "Host": host})

    if should_allow:
        assert "Access-Control-Allow-Origin" in res.headers
    else:
        assert "Access-Control-Allow-Origin" not in res.headers


async def test_cors_middleware_does_not_wrap_send_for_non_http_scopes() -> None:
    """CORS is HTTP-only. ``ASGIMiddleware`` does not enforce ``scopes`` at runtime for
    app-level middleware, so the guard must be explicit: a websocket scope carrying an
    ``Origin`` header must reach the next app with the *original* ``send``."""
    received_sends: list[Any] = []

    async def next_app(scope: Any, receive: Any, send: Any) -> None:
        received_sends.append(send)

    async def send(message: Any) -> None: ...  # pragma: no cover

    async def receive() -> Any: ...  # pragma: no cover

    asgi_app = CORSMiddleware(allow_origins=["*"])(next_app)
    scope = {"type": "websocket", "headers": [(b"origin", b"http://www.example.com")]}

    await asgi_app(cast("Any", scope), receive, send)

    assert received_sends == [send]
