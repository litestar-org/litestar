from typing import Any

import pytest

from litestar import asgi, get
from litestar.config.allowed_hosts import AllowedHostsConfig
from litestar.enums import ScopeType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware.allowed_hosts import AllowedHostsMiddleware
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client
from litestar.types import Receive, Scope, Scopes, Send


def test_allowed_hosts_middleware_hosts_regex() -> None:
    middleware = AllowedHostsMiddleware(allowed_hosts=["*.example.com", "moishe.zuchmir.com"])
    assert middleware.allowed_hosts_regex is not None
    assert middleware.allowed_hosts_regex.pattern == r".*\.example\.com$|moishe\.zuchmir\.com"

    assert middleware.allowed_hosts_regex.fullmatch("www.example.com")
    assert middleware.allowed_hosts_regex.fullmatch("other.example.com")
    assert middleware.allowed_hosts_regex.fullmatch("x.y.z.example.com")
    assert middleware.allowed_hosts_regex.fullmatch("moishe.zuchmir.com")

    assert not middleware.allowed_hosts_regex.fullmatch("www.example.x.com")
    assert not middleware.allowed_hosts_regex.fullmatch("josh.zuchmir.com")
    assert not middleware.allowed_hosts_regex.fullmatch("x.moishe.zuchmir.com")
    assert not middleware.allowed_hosts_regex.fullmatch("moishe.zuchmir.x.com")


def test_allowed_hosts_middleware_redirect_regex() -> None:
    middleware = AllowedHostsMiddleware(
        allowed_hosts=["*.example.com", "www.moishe.zuchmir.com", "www.yada.bada.bing.io", "example.com"]
    )
    assert middleware.redirect_domains is not None
    assert middleware.redirect_domains.pattern == "moishe.zuchmir.com|yada.bada.bing.io"

    assert middleware.redirect_domains.fullmatch("moishe.zuchmir.com")
    assert middleware.redirect_domains.fullmatch("yada.bada.bing.io")


@pytest.mark.parametrize(
    "base_url,forwarded_host,expected_status_code",
    [
        ("http://x.example.com", None, HTTP_200_OK),
        ("http://x.y.example.com", None, HTTP_200_OK),
        ("http://moishe.zuchmir.com", None, HTTP_200_OK),
        ("http://moisheAzuchmir.com", None, HTTP_400_BAD_REQUEST),
        ("http://x.moishe.zuchmir.com", None, HTTP_400_BAD_REQUEST),
        (None, "x.example.com", HTTP_400_BAD_REQUEST),
    ],
)
def test_middleware_allowed_hosts(
    base_url: str | None,
    forwarded_host: str | None,
    expected_status_code: int,
) -> None:
    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    config = AllowedHostsConfig(allowed_hosts=["*.example.com", "moishe.zuchmir.com"])

    with create_test_client(handler, allowed_hosts=config) as client:
        if base_url:
            client.base_url = base_url
        if not base_url:
            client.headers["host"] = ""
        if forwarded_host:
            client.headers["x-forwarded-host"] = forwarded_host
        response = client.get("/")
        assert response.status_code == expected_status_code


def test_middleware_allow_all() -> None:
    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    # contrived case - but if "*" is in hosts, we allow all.
    config = AllowedHostsConfig(allowed_hosts=["*", "*.example.com", "moishe.zuchmir.com"])

    with create_test_client(handler, allowed_hosts=config) as client:
        client.base_url = "http://any.domain.allowed.com"
        response = client.get("/")
        assert response.status_code == HTTP_200_OK


def test_middleware_redirect_on_www_by_default() -> None:
    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    config = AllowedHostsConfig(allowed_hosts=["www.moishe.zuchmir.com"])

    with create_test_client(handler, allowed_hosts=config) as client:
        client.base_url = "http://moishe.zuchmir.com"
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert str(response.url) == "http://www.moishe.zuchmir.com/"


def test_middleware_does_not_redirect_when_off() -> None:
    @get("/")
    def handler() -> dict:
        return {"hello": "world"}

    config = AllowedHostsConfig(allowed_hosts=["www.moishe.zuchmir.com"], www_redirect=False)

    with create_test_client(handler, allowed_hosts=config) as client:
        client.base_url = "http://moishe.zuchmir.com"
        response = client.get("/")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_validation_raises_for_wrong_wildcard_domain() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        AllowedHostsConfig(allowed_hosts=["www.moishe.*.com"])


@pytest.mark.parametrize("scopes", [None, {ScopeType.HTTP}, {ScopeType.HTTP, ScopeType.WEBSOCKET}])
def test_middleware_applies_to_asgi_route_handlers(scopes: "Scopes | None") -> None:
    @asgi("/raw", is_mount=False)
    async def raw(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"value", "more_body": False})

    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], scopes=scopes)

    with create_test_client([raw], allowed_hosts=config) as client:
        client.base_url = "http://not.allowed.com"
        assert client.get("/raw").status_code == HTTP_400_BAD_REQUEST

        client.base_url = "http://moishe.zuchmir.com"
        assert client.get("/raw").status_code == HTTP_200_OK


def test_middleware_exclude_skips_matching_handler_paths() -> None:
    @get("/checked")
    def checked() -> None: ...

    @get("/skipped")
    def skipped() -> None: ...

    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], exclude="^/skipped")

    with create_test_client([checked, skipped], allowed_hosts=config) as client:
        client.base_url = "http://not.allowed.com"
        assert client.get("/checked").status_code == HTTP_400_BAD_REQUEST
        assert client.get("/skipped").status_code == HTTP_200_OK


def test_middleware_exclude_opt_key_skips_flagged_handlers() -> None:
    @get("/checked")
    def checked() -> None: ...

    @get("/skipped", opt={"skip_hosts": True})
    def skipped() -> None: ...

    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], exclude_opt_key="skip_hosts")

    with create_test_client([checked, skipped], allowed_hosts=config) as client:
        client.base_url = "http://not.allowed.com"
        assert client.get("/checked").status_code == HTTP_400_BAD_REQUEST
        assert client.get("/skipped").status_code == HTTP_200_OK


def test_scopes_wiring_bypasses_unlisted_scope_types() -> None:
    @get("/http")
    def http_handler() -> None: ...

    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], scopes={ScopeType.WEBSOCKET})

    with create_test_client([http_handler], allowed_hosts=config) as client:
        client.base_url = "http://not.allowed.com"
        assert client.get("/http").status_code == HTTP_200_OK


def _ws_mount() -> "Any":
    @asgi("/mounted", is_mount=True)
    async def mounted(scope: Scope, receive: Receive, send: Send) -> None:
        await receive()
        await send({"type": "websocket.accept", "subprotocol": None, "headers": []})
        await send({"type": "websocket.send", "text": "ws-ok", "bytes": None})
        await send({"type": "websocket.close", "code": 1000, "reason": None})

    return mounted


def test_scopes_websocket_checks_connections_to_asgi_mounts() -> None:
    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], scopes={ScopeType.WEBSOCKET})

    with (
        create_test_client([_ws_mount()], allowed_hosts=config, base_url="http://moishe.zuchmir.com") as client,
        client.websocket_connect("/mounted") as ws,
    ):
        assert ws.receive_text() == "ws-ok"

    with create_test_client([_ws_mount()], allowed_hosts=config, base_url="http://not.allowed.com") as client:
        with pytest.raises(ExceptionGroup):
            with client.websocket_connect("/mounted") as ws:
                ws.receive_text()


def test_scopes_http_does_not_check_websocket_connections_to_asgi_mounts() -> None:
    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], scopes={ScopeType.HTTP})

    with (
        create_test_client([_ws_mount()], allowed_hosts=config, base_url="http://not.allowed.com") as client,
        client.websocket_connect("/mounted") as ws,
    ):
        assert ws.receive_text() == "ws-ok"


def test_exclude_matches_handler_path_template() -> None:
    from litestar.params import FromPath

    @get("/user/{user_id:int}")
    def excluded(user_id: FromPath[int]) -> None: ...

    @get("/order/{order_id:int}")
    def checked(order_id: FromPath[int]) -> None: ...

    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], exclude=[r"/user/\{user_id:int\}"])

    with create_test_client([excluded, checked], allowed_hosts=config) as client:
        client.base_url = "http://not.allowed.com"
        assert client.get("/user/1").status_code == HTTP_200_OK
        assert client.get("/order/1").status_code == HTTP_400_BAD_REQUEST

    # a request-path pattern does not match a dynamic handler and excludes nothing
    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], exclude=["^/user/1$"])

    with create_test_client([excluded, checked], allowed_hosts=config) as client:
        client.base_url = "http://not.allowed.com"
        assert client.get("/user/1").status_code == HTTP_400_BAD_REQUEST


def test_empty_scopes_set_uses_default_scopes() -> None:
    @get("/http")
    def http_handler() -> None: ...

    config = AllowedHostsConfig(allowed_hosts=["moishe.zuchmir.com"], scopes=set())

    with create_test_client([http_handler], allowed_hosts=config) as client:
        client.base_url = "http://not.allowed.com"
        assert client.get("/http").status_code == HTTP_400_BAD_REQUEST
