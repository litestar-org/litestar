import pytest

from starlite import BaseRouteHandler
from starlite.exceptions import ImproperlyConfiguredException


def test_raise_no_fn_validation() -> None:
    handler = BaseRouteHandler[BaseRouteHandler](path="/")

    with pytest.raises(ImproperlyConfiguredException):
        handler._validate_handler_function()
