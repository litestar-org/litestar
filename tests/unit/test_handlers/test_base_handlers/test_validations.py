from dataclasses import dataclass

import pytest

from litestar import Litestar, post
from litestar.dto import DTOData
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers.base import BaseRouteHandler


def test_raise_no_fn_validation() -> None:
    handler = BaseRouteHandler(path="/")

    with pytest.raises(ImproperlyConfiguredException):
        handler.fn


def test_dto_data_annotation_with_no_resolved_dto() -> None:
    @dataclass
    class Model:
        """Example dataclass model."""

        hello: str

    @post("/")
    async def async_hello_world(data: DTOData[Model]) -> Model:
        """Route Handler that outputs hello world."""
        return data.create_instance()

    with pytest.raises(ImproperlyConfiguredException):
        Litestar(route_handlers=[async_hello_world])
