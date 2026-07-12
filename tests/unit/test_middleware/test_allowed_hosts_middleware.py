from typing import TYPE_CHECKING, Any, cast

import pytest

from litestar import get
from litestar.config.allowed_hosts import AllowedHostsConfig
from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware import MiddlewareProtocol
from litestar.middleware.allowed_hosts import AllowedHostsMiddleware
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send


class DummyApp(MiddlewareProtocol):
    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        return


def test_allowed_hosts_middleware() -> None:
    @get(path="/")
    def handler() -> None: ...

    client = create_test_client(route_handlers=[handler], allowed_hosts=["*.example.com", "moishe.zuchmir.com"])
    unpacked_middleware = []
    cur = client.app.asgi_router.root_route_map_node.children["/"].asgi_handlers["GET"][0]
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cast("Any", cur.app)  # pyright: ignore[reportFunctionMemberAccess]
    unpacked_middleware.append(cur)

    allowed_hosts_middleware, *_ = unpacked_middleware
    assert isinstance(allowed_hosts_middleware, AllowedHostsMiddleware)
    assert allowed_hosts_middleware.allowed_hosts_regex.pattern == r".*\.example\.com$|moishe\.zuchmir\.com"  # type: ignore[union-attr]


def test_allowed_hosts_middleware_hosts_regex() -> None:
    config = AllowedHostsConfig(allowed_hosts=["*.example.com", "moishe.zuchmir.com"])
    middleware = AllowedHostsMiddleware(app=DummyApp(), config=config)  # type: ignore[abstract]
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
    config = AllowedHostsConfig(
        allowed_hosts=["*.example.com", "www.moishe.zuchmir.com", "www.yada.bada.bing.io", "example.com"]
    )
    middleware = AllowedHostsMiddleware(app=DummyApp(), config=config)  # type: ignore[abstract]
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


def test_allowed_hosts_strips_port_from_host_header() -> None:
    """Test that AllowedHostsMiddleware strips the port from the Host header before matching."""
    from litestar import Litestar
    from litestar.testing import TestClient

    @get(path="/")
    def handler() -> None: ...

    client = TestClient(app=Litestar(route_handlers=[handler], allowed_hosts=["localhost"]))
    
    # Without port - should work
    response = client.get("/", headers={"Host": "localhost"})
    assert response.status_code == HTTP_200_OK
    
    # With port - should also work (port stripped before matching)
    response = client.get("/", headers={"Host": "localhost:8000"})
    assert response.status_code == HTTP_200_OK
