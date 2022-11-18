from typing import TYPE_CHECKING, Any

import pytest

from starlite import BaseRouteHandler, HttpMethod, HTTPRouteHandler, Response, Starlite
from starlite.constants import STARLITE
from starlite.utils import (
    get_serializer_from_scope,
    get_starlite_scope_state,
    set_starlite_scope_state,
)

if TYPE_CHECKING:
    from starlite.types.asgi_types import HTTPScope


@pytest.fixture()
def scope() -> "HTTPScope":
    return {"state": {}}  # type:ignore[typeddict-item]


def test_get_serializer_from_scope() -> None:
    class MyResponse(Response):
        @staticmethod
        def serializer(value: Any) -> Any:
            return value

    assert get_serializer_from_scope({"app": Starlite([]), "route_handler": BaseRouteHandler()}) is None  # type: ignore
    assert (
        get_serializer_from_scope(
            {"app": Starlite([], response_class=MyResponse), "route_handler": BaseRouteHandler(path="/")}  # type: ignore
        )
        is MyResponse.serializer
    )
    assert (
        get_serializer_from_scope(
            {
                "app": Starlite([]),
                "route_handler": HTTPRouteHandler(path="/", http_method=HttpMethod.GET, response_class=MyResponse),  # type: ignore
            }
        )
        is MyResponse.serializer
    )


def test_get_starlite_scope_state_sets_starlite_key_in_scope_state(scope: "HTTPScope") -> None:
    get_starlite_scope_state(scope, "key")
    assert STARLITE in scope["state"]
    assert scope["state"][STARLITE]["key"] is None


def test_get_starlite_scope_state_set_default(scope: "HTTPScope") -> None:
    value = get_starlite_scope_state(scope, "key", "value")
    assert scope["state"][STARLITE]["key"] == "value" == value


def test_set_starlite_scope_state(scope: "HTTPScope") -> None:
    set_starlite_scope_state(scope, "key", "value")
    assert scope["state"][STARLITE]["key"] == "value"
