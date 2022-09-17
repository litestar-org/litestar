from typing import Any

from starlite import BaseRouteHandler, HttpMethod, HTTPRouteHandler, Response, Starlite
from starlite.utils import get_serializer_from_scope


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
