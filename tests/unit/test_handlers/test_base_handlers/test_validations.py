import pytest

from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers.base import BaseRouteHandler


def test_raise_no_fn_validation() -> None:
    handler = BaseRouteHandler(path="/")

    with pytest.raises(ImproperlyConfiguredException):
        handler.fn
