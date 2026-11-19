from __future__ import annotations

import pytest

from litestar import Litestar, get, head, query, route
from litestar._openapi.path_item import merge_path_item_operations
from litestar._openapi.typescript_converter.converter import convert_openapi_to_typescript
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Operation, PathItem
from litestar.params import FromPath, JSONBody
from tests.unit.test_openapi.utils import build_document


@query("/search")
async def search(data: JSONBody[dict[str, str]]) -> list[str]:
    return list(data)


def test_query_operation_is_documented_from_openapi_3_2() -> None:
    schema = build_document(search, openapi_version="3.2.0")

    operation = schema["paths"]["/search"]["query"]
    assert operation["operationId"] == "SearchSearch"
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "type": "object",
        "additionalProperties": {"type": "string"},
    }
    assert "200" in operation["responses"]


def test_query_operation_is_omitted_from_openapi_3_1() -> None:
    @get("/search")
    async def list_all() -> list[str]:
        return []

    schema = build_document(search, list_all, openapi_version="3.1.0")

    assert set(schema["paths"]["/search"]) == {"get"}


def test_path_with_only_a_query_operation_is_omitted_from_openapi_3_1() -> None:
    schema = build_document(search, openapi_version="3.1.0")

    assert "/search" not in schema["paths"]


def test_query_operation_of_multi_method_handler() -> None:
    @route("/items", http_method=["GET", "QUERY"])
    async def items() -> list[str]:
        return []

    path_item = build_document(items, openapi_version="3.2.0")["paths"]["/items"]
    assert path_item["get"]["operationId"] == "ItemsGetItems"
    assert path_item["query"]["operationId"] == "ItemsQueryItems"


def test_query_operation_merged_with_operations_of_same_path_format() -> None:
    @get("/items/{item_id:int}")
    async def get_item(item_id: FromPath[int]) -> None:
        return None

    @head("/items/{item_id:str}")
    async def head_item(item_id: FromPath[str]) -> None:
        return None

    @query("/items/{item_id:uuid}")
    async def query_item(item_id: FromPath[str]) -> None:
        return None

    schema = build_document(get_item, head_item, query_item, openapi_version="3.2.0")

    assert set(schema["paths"]["/items/{item_id}"]) == {"get", "head", "query"}


@pytest.mark.parametrize("query_first", [True, False], ids=["query-first", "get-first"])
def test_merge_path_item_operations_keeps_the_query_operation(query_first: bool) -> None:
    query_operation = Operation(operation_id="query")
    get_operation = Operation(operation_id="get")
    query_item, get_item = PathItem(query=query_operation), PathItem(get=get_operation)

    merged = merge_path_item_operations(
        *((query_item, get_item) if query_first else (get_item, query_item)), for_path="/"
    )

    assert merged.query is query_operation
    assert merged.get is get_operation


def test_typescript_converter_includes_query_operation() -> None:
    result = convert_openapi_to_typescript(
        Litestar(
            [search], openapi_config=OpenAPIConfig(title="test", version="1", openapi_version="3.2.0")
        ).openapi_schema
    ).write()

    assert result.index("export type RequestBody") > result.index("export namespace SearchSearch {")
