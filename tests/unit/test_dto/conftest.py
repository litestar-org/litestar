# ruff: noqa: UP006
from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import pytest

from litestar import Request, get
from litestar.enums import MediaType
from litestar.testing import RequestFactory

from . import Model

if TYPE_CHECKING:
    from typing import Any

T = TypeVar("T", bound=Model)


@pytest.fixture()
def asgi_connection() -> Request[Any, Any, Any]:
    @get("/", name="handler_id", media_type=MediaType.JSON)
    def _handler() -> None:
        ...

    return RequestFactory().get(path="/", route_handler=_handler)
