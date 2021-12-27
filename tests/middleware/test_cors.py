from starlette.middleware.cors import CORSMiddleware

from starlite import CORSConfig, create_test_client, get


@get(path="/")
def handler() -> None:
    ...


def test_cors():
    cors_config = CORSConfig()
    assert cors_config.allow_credentials is False
    assert cors_config.allow_headers == ["*"]
    assert cors_config.allow_methods == ["*"]
    assert cors_config.allow_origins == ["*"]
    assert cors_config.allow_origin_regex is None
    assert cors_config.max_age == 600
    assert cors_config.expose_headers == []

    client = create_test_client(route_handlers=[handler], cors_config=cors_config)
    unpacked_middleware = []
    cur = client.app.middleware_stack
    while hasattr(cur, "app"):
        unpacked_middleware.append(cur)
        cur = cur.app
    assert len(unpacked_middleware) == 3
    cors_middleware = unpacked_middleware[1]
    assert isinstance(cors_middleware, CORSMiddleware)
    assert cors_middleware.allow_headers == ["*", "accept", "accept-language", "content-language", "content-type"]
    assert cors_middleware.allow_methods == ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")
    assert cors_middleware.allow_origins == cors_config.allow_origins
    assert cors_middleware.allow_origin_regex == cors_config.allow_origin_regex
