from litestar import Litestar, Request, Response
from litestar.connection import ASGIConnection
from litestar.exceptions import ValidationException
from litestar.handlers import BaseRouteHandler
from litestar.static_files import create_static_router


def test_route_reverse() -> None:
    app = Litestar(route_handlers=[create_static_router(path="/static", directories=["something"], name="static")])

    assert app.route_reverse("static", file_path="foo.py") == "/static/foo.py"


def test_opt() -> None:
    router = create_static_router(path="/", directories=["something"], opt={"foo": "bar"})

    assert router.opt == {"foo": "bar"}


def test_guards() -> None:
    def guard(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
        pass

    router = create_static_router(path="/", directories=["something"], guards=[guard])

    assert router.guards == [guard]


def test_exception_handlers() -> None:
    def handle(request: Request, exception: Exception) -> Response:
        return Response(b"")

    exception_handlers = {ValidationException: handle}

    router = create_static_router(path="/", directories=["something"], exception_handlers=exception_handlers)  # type: ignore[arg-type]

    assert router.exception_handlers == exception_handlers
