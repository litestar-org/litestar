from starlette.middleware.trustedhost import TrustedHostMiddleware

from starlite import create_test_client, get


@get(path="/")
def handler() -> None:
    ...


def test_trusted_hosts_middleware():
    client = create_test_client(route_handlers=[handler], allowed_hosts=["*"])
    unpacked_middleware = []
    cur = client.app.middleware_stack
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cur.app
    assert len(unpacked_middleware) == 2
    trusted_hosts_middleware = unpacked_middleware[0]
    assert isinstance(trusted_hosts_middleware, TrustedHostMiddleware)
    assert trusted_hosts_middleware.allowed_hosts == ["*"]
