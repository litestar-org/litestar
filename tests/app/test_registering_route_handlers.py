import pytest

from starlite import Starlite, get
from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.exceptions import ImproperlyConfiguredException


def test_registering_openapi_docs_without_openapi_config_raises() -> None:
    def fn() -> None:
        return

    app = Starlite(route_handlers=[], openapi_config=None)

    with pytest.raises(ImproperlyConfiguredException):
        app.register(get("/path1")(fn), add_to_openapi_schema=True)


def test_registering_route_handler_generates_openapi_docs() -> None:
    def fn() -> None:
        return

    app = Starlite(route_handlers=[], openapi_config=DEFAULT_OPENAPI_CONFIG)
    assert app.openapi_schema

    app.register(get("/path1")(fn))

    paths = app.openapi_schema.paths

    assert paths is not None
    assert not paths.get("/path1")

    app.register(get("/path2")(fn), add_to_openapi_schema=True)
    assert paths.get("/path2")
