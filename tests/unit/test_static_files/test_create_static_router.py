from litestar import Litestar
from litestar.exceptions import ValidationException
from litestar.static_files import create_static_router


def test_route_reverse() -> None:
    app = Litestar(route_handlers=[create_static_router(path="/static", directories=["something"], name="static")])

    assert app.route_reverse("static", file_path="foo.py") == "/static/foo.py"


def test_opt() -> None:
    router = create_static_router(path="/", directories=["something"], opt={"foo": "bar"})

    assert router.opt == {"foo": "bar"}


def test_guards() -> None:
    def guard():
        pass

    router = create_static_router(path="/", directories=["something"], guards=[guard])

    assert router.guards == [guard]


def test_exception_handlers() -> None:
    def handle():
        pass

    exception_handlers = {ValidationException: handle}

    router = create_static_router(path="/", directories=["something"], exception_handlers=exception_handlers)

    assert router.exception_handlers == exception_handlers
