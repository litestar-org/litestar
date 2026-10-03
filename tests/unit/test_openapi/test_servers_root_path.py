from litestar import get
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Server
from litestar.testing import create_test_client


@get("/ping", sync_to_thread=False)
def ping() -> str:
    return "pong"


def _config(**kwargs: object) -> OpenAPIConfig:
    return OpenAPIConfig(title="t", version="1", **kwargs)  # type: ignore[arg-type]


def test_openapi_servers_use_asgi_root_path_when_default() -> None:
    with create_test_client([ping], openapi_config=_config(), root_path="/api") as client:
        schema = client.get("/schema/openapi.json").json()
        servers = schema.get("servers") or []
        assert servers, "servers missing from OpenAPI schema"
        assert servers[0]["url"] == "/api"


def test_openapi_servers_keep_explicit_config_over_root_path() -> None:
    config = _config(servers=[Server(url="https://example.com/v1")])
    with create_test_client([ping], openapi_config=config, root_path="/api") as client:
        schema = client.get("/schema/openapi.json").json()
        servers = schema.get("servers") or []
        assert servers[0]["url"] == "https://example.com/v1"


def test_openapi_servers_default_without_root_path() -> None:
    with create_test_client([ping], openapi_config=_config()) as client:
        schema = client.get("/schema/openapi.json").json()
        servers = schema.get("servers") or []
        assert servers[0]["url"] == "/"
