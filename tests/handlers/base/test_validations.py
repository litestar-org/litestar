import pytest

from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.base import BaseRouteHandler


def test_raise_no_fn_validation() -> None:
    handler = BaseRouteHandler[BaseRouteHandler](path="/")

    with pytest.raises(ImproperlyConfiguredException):
        handler.fn
