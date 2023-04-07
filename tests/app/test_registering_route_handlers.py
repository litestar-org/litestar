from litestar import Litestar, get


def test_registering_route_handler_generates_openapi_docs() -> None:
    def fn() -> None:
        return

    app = Litestar(route_handlers=[])
    assert app.openapi_schema

    app.register(get("/path1")(fn))

    paths = app.openapi_schema.paths

    assert paths is not None
    assert paths.get("/path1")

    app.register(get("/path2")(fn))
    assert paths.get("/path2")
