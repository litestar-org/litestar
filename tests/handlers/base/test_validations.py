import pytest

from starlite import BaseRouteHandler, ImproperlyConfiguredException


def test_raise_no_fn_validation() -> None:
    handler = BaseRouteHandler[BaseRouteHandler](path="/")

    with pytest.raises(ImproperlyConfiguredException):
        handler.validate_handler_function()

    with pytest.raises(RuntimeError):
        handler.resolve_dependencies()
