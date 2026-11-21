from __future__ import annotations

from typing import Any, cast

from litestar import Litestar, get, query, route
from litestar.handlers import HTTPRouteHandler
from litestar.params import JSONBody


@query("/search")
async def search(data: JSONBody[dict[str, str]]) -> list[str]:
    return list(data)


def _paths(*route_handlers: HTTPRouteHandler) -> dict[str, Any]:
    return cast("dict[str, Any]", Litestar(list(route_handlers)).openapi_schema.to_schema()["paths"])


def test_query_operation_is_omitted() -> None:
    @get("/search")
    async def list_all() -> list[str]:
        return []

    assert set(_paths(search, list_all)["/search"]) == {"get"}


def test_path_with_only_a_query_operation_is_omitted() -> None:
    assert "/search" not in _paths(search)


def test_query_operation_of_multi_method_handler_is_omitted() -> None:
    @route("/items", http_method=["GET", "QUERY"])
    async def items() -> list[str]:
        return []

    assert set(_paths(items)["/items"]) == {"get"}
