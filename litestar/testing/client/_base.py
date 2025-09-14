from __future__ import annotations

from http.cookiejar import CookieJar
from typing import TYPE_CHECKING, Any

from litestar.connection import ASGIConnection
from litestar.datastructures import MutableScopeHeaders
from litestar.enums import ScopeType
from litestar.types import ASGIApp, HTTPResponseStartEvent, HTTPScope
from litestar.utils.scope.state import ScopeState

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from httpx._client import UseClientDefault
    from httpx._types import (
        CookieTypes,
        HeaderTypes,
        QueryParamTypes,
        TimeoutTypes,
    )

    from litestar.testing import AsyncTestClient, TestClient


import httpx
from httpx._client import USE_CLIENT_DEFAULT, UseClientDefault


def fake_http_send_message(headers: MutableScopeHeaders) -> HTTPResponseStartEvent:
    headers.setdefault("content-type", "application/text")
    return HTTPResponseStartEvent(type="http.response.start", status=200, headers=headers.headers)


def fake_asgi_connection(app: ASGIApp, cookies: dict[str, str]) -> ASGIConnection[Any, Any, Any, Any]:
    scope: HTTPScope = {
        "type": ScopeType.HTTP,
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "headers": [],
        "method": "GET",
        "http_version": "1.1",
        "extensions": {"http.response.template": {}},
        "app": app,  # type: ignore[typeddict-item]
        "litestar_app": app,
        "state": {},
        "path_params": {},
        "route_handler": None,
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "auth": None,
        "session": None,
        "user": None,
    }
    ScopeState.from_scope(scope).cookies = cookies
    return ASGIConnection[Any, Any, Any, Any](scope=scope)


def _prepare_ws_connect_request(
    client: httpx.Client | httpx.AsyncClient,
    url: str,
    subprotocols: Sequence[str] | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    extensions: Mapping[str, Any] | None = None,
) -> httpx.Request:
    default_headers: dict[str, str] = {}
    default_headers.setdefault("connection", "upgrade")
    default_headers.setdefault("sec-websocket-key", "testserver==")
    default_headers.setdefault("sec-websocket-version", "13")
    if subprotocols is not None:
        default_headers.setdefault("sec-websocket-protocol", ", ".join(subprotocols))
    return client.build_request(
        "GET",
        client.base_url.copy_with(scheme="ws").join(url),
        headers={**dict(headers or {}), **default_headers},  # type: ignore[misc]
        params=params,
        cookies=cookies,
        extensions=None if extensions is None else dict(extensions),
        timeout=timeout,
    )


async def _set_session_data(client: TestClient | AsyncTestClient, data: dict[str, Any]) -> None:
    mutable_headers = MutableScopeHeaders()
    connection = fake_asgi_connection(
        app=client.app,
        cookies=dict(client.cookies),
    )
    session_id = client._session_backend.get_session_id(connection)
    connection._connection_state.session_id = session_id  # pyright: ignore [reportGeneralTypeIssues]
    await client._session_backend.store_in_message(
        scope_session=data, message=fake_http_send_message(mutable_headers), connection=connection
    )
    response = httpx.Response(200, request=httpx.Request("GET", client.base_url), headers=mutable_headers.headers)

    cookies = httpx.Cookies(CookieJar())
    cookies.extract_cookies(response)
    client.cookies.update(cookies)


async def _get_session_data(client: TestClient | AsyncTestClient) -> dict[str, Any]:
    return await client._session_backend.load_from_connection(
        connection=fake_asgi_connection(
            app=client.app,
            cookies=dict(client.cookies),
        ),
    )
