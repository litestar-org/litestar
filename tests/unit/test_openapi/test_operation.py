from dataclasses import dataclass
from datetime import time
from typing import Annotated, Any, Generic, Optional, TypeVar

import pytest

from litestar import Controller, Response, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.dto import DataclassDTO
from litestar.params import (
    FromHeader,
    FromPath,
    FromQuery,
    HeaderParameter,
    JSONBody,
    PathParameter,
    QueryParameter,
)
from litestar.response import File, Stream
from litestar.testing import create_test_client
from litestar.typing import FieldDefinition
from tests.unit.test_openapi.utils import build_document

T = TypeVar("T")


@dataclass
class Item:
    name: str


@dataclass
class Page(Generic[T]):
    items: list[T]


def test_request_body_of_unused_dependency_is_not_documented() -> None:
    async def provide_item(data: JSONBody[Item]) -> Item:
        return data

    @post("/used")
    async def used(item: NamedDependency[Item]) -> None:
        return None

    @post("/unused")
    async def unused() -> None:
        return None

    document = build_document(used, unused, app_kwargs={"dependencies": {"item": Provide(provide_item)}})

    assert "requestBody" in document["paths"]["/used"]["post"]
    assert "400" in document["paths"]["/used"]["post"]["responses"]
    assert "requestBody" not in document["paths"]["/unused"]["post"]
    assert "400" not in document["paths"]["/unused"]["post"]["responses"]


@pytest.mark.parametrize("media_type, expected", [(None, "application/octet-stream"), ("image/png", "image/png")])
def test_file_response_content_key(media_type: str | None, expected: str) -> None:
    @get("/", media_type=media_type)
    async def handler() -> File:
        raise NotImplementedError

    document = build_document(handler)

    assert list(document["paths"]["/"]["get"]["responses"]["200"]["content"]) == [expected]


def test_response_with_return_dto_content_key() -> None:
    @get("/", return_dto=DataclassDTO[Item])
    async def handler() -> Response[Item]:
        raise NotImplementedError

    document = build_document(handler)

    assert list(document["paths"]["/"]["get"]["responses"]["200"]["content"]) == ["application/json"]


def test_time_format() -> None:
    @get("/")
    async def handler(at: FromQuery[time]) -> None:
        return None

    document = build_document(handler)

    assert document["paths"]["/"]["get"]["parameters"][0]["schema"] == {"type": "string", "format": "time"}


def test_generic_component_names() -> None:
    @get("/items")
    async def items() -> Page[Item]:
        raise NotImplementedError

    @get("/numbers")
    async def numbers() -> Page[int]:
        raise NotImplementedError

    @get("/nested")
    async def nested() -> Page[list[Item]]:
        raise NotImplementedError

    document = build_document(items, numbers, nested)

    assert list(document["components"]["schemas"]) == ["Item", "Page_Item", "Page_int", "Page_list_Item"]
    assert document["paths"]["/items"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Page_Item"
    }


def test_generic_component_names_spell_unions_alike() -> None:
    @get("/pipe")
    async def pipe() -> Page[int | None]:
        raise NotImplementedError

    @get("/optional")
    async def optional() -> Page[Optional[str]]:
        raise NotImplementedError

    document = build_document(pipe, optional)

    assert list(document["components"]["schemas"]) == ["Page_Union_int_None", "Page_Union_str_None"]


def test_schema_component_name_creator() -> None:
    @get("/items")
    async def items() -> Page[Item]:
        raise NotImplementedError

    def name_creator(field_definition: FieldDefinition) -> str:
        if field_definition.inner_types:
            return f"{field_definition.inner_types[0].annotation.__name__}{field_definition.origin.__name__}"
        return f"Api {field_definition.annotation.__name__}"

    document = build_document(items, schema_component_name_creator=name_creator)

    assert list(document["components"]["schemas"]) == ["Api_Item", "ItemPage"]
    assert document["components"]["schemas"]["ItemPage"]["properties"]["items"]["items"] == {
        "$ref": "#/components/schemas/Api_Item"
    }


def test_schema_component_name_creator_returning_same_name_for_different_types() -> None:
    @get("/items")
    async def items() -> Page[Item]:
        raise NotImplementedError

    @get("/numbers")
    async def numbers() -> Page[int]:
        raise NotImplementedError

    document = build_document(
        items,
        numbers,
        schema_component_name_creator=lambda _: "Model",
    )

    schemas = document["components"]["schemas"]
    assert len(schemas) == 3
    assert {schema["title"] for schema in schemas.values()} == {"Item", "Page[Item]", "Page[int]"}
    for path in ("/items", "/numbers"):
        ref = document["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert ref.removeprefix("#/components/schemas/") in schemas


def _documented_parameters(document: dict[str, Any], path: str) -> list[tuple[str, str]]:
    return [(parameter["name"], parameter["in"]) for parameter in document["paths"][path]["get"]["parameters"]]


def test_renamed_path_parameter_is_documented_at_its_path_position() -> None:
    @get("/{first:int}/{second:int}")
    async def handler(page: FromQuery[int], local: Annotated[int, PathParameter(name="second")]) -> None:
        return None

    document = build_document(handler)

    assert _documented_parameters(document, "/{first}/{second}") == [
        ("first", "path"),
        ("second", "path"),
        ("page", "query"),
    ]


def test_path_parameters_are_documented_before_layered_parameters() -> None:
    @get("/{first:int}/{second:int}")
    async def handler(shared: FromQuery[int], second: FromPath[int], own: FromQuery[int]) -> None:
        return None

    document = build_document(
        Router(
            "/",
            route_handlers=[handler],
            parameters={"shared": QueryParameter(annotation=int), "trace": QueryParameter(annotation=str)},
        )
    )

    assert _documented_parameters(document, "/{first}/{second}") == [
        ("first", "path"),
        ("second", "path"),
        ("shared", "query"),
        ("trace", "query"),
        ("own", "query"),
    ]


def test_path_parameters_of_a_handler_on_several_paths_follow_each_path() -> None:
    @get(["/items", "/items/{first:int}", "/items/{second:int}/{first:int}"])
    async def handler(
        page: FromQuery[int], first: FromPath[int | None] = None, second: FromPath[int | None] = None
    ) -> None:
        return None

    document = build_document(handler)

    assert _documented_parameters(document, "/items") == [("page", "query")]
    assert _documented_parameters(document, "/items/{first}") == [("first", "path"), ("page", "query")]
    assert _documented_parameters(document, "/items/{second}/{first}") == [
        ("second", "path"),
        ("first", "path"),
        ("page", "query"),
    ]


def test_dependency_parameters_follow_the_handler_parameters() -> None:
    async def provide_dd(dq1: FromQuery[int], p: FromPath[int]) -> int:
        return p

    @get("/d/{o:int}/{p:int}", dependencies={"dd": Provide(provide_dd)})
    async def handler(first: FromQuery[int], dd: NamedDependency[int], last: FromQuery[int]) -> None:
        return None

    assert _documented_parameters(build_document(handler), "/d/{o}/{p}") == [
        ("o", "path"),
        ("p", "path"),
        ("first", "query"),
        ("last", "query"),
        ("dq1", "query"),
    ]


def test_path_parameter_consumed_by_handler_and_dependency_is_documented_once() -> None:
    async def provide_a(a: FromPath[int]) -> int:
        return a

    @get("/{z:int}/{a:int}", dependencies={"provided": Provide(provide_a)})
    async def handler(q: FromQuery[int], a: FromPath[int], provided: NamedDependency[int]) -> None:
        return None

    assert _documented_parameters(build_document(handler), "/{z}/{a}") == [
        ("z", "path"),
        ("a", "path"),
        ("q", "query"),
    ]


def test_empty_security_lifts_requirements_of_outer_layers() -> None:
    @get("/public")
    async def public() -> None:
        return None

    @get("/scoped", security=[{"oauth": ["read"]}])
    async def scoped() -> None:
        return None

    class PublicController(Controller):
        path = "/controller"
        security = []

        @get("/public")
        async def public(self) -> None:
            return None

    @get("/handler", security=[])
    async def handler() -> None:
        return None

    @get("/protected")
    async def protected() -> None:
        return None

    document = build_document(
        Router("/router", route_handlers=[public, scoped], security=[]),
        PublicController,
        handler,
        protected,
        app_kwargs={"security": [{"apiKey": []}]},
    )

    assert document["paths"]["/router/public"]["get"]["security"] == []
    assert document["paths"]["/router/scoped"]["get"]["security"] == [{"oauth": ["read"]}]
    assert document["paths"]["/controller/public"]["get"]["security"] == []
    assert document["paths"]["/handler"]["get"]["security"] == []
    assert document["paths"]["/protected"]["get"]["security"] == [{"apiKey": []}]


def test_application_without_security_does_not_emit_empty_security() -> None:
    @get("/")
    async def handler() -> None:
        return None

    assert "security" not in build_document(handler, app_kwargs={"security": []})["paths"]["/"]["get"]


@pytest.mark.parametrize(
    "openapi_version, media_type, expected",
    [
        ("3.2.0", "application/jsonl", {"application/jsonl": {"itemSchema": {}}}),
        ("3.1.0", "application/jsonl", {"application/jsonl": {"schema": {}}}),
        ("3.2.0", "text/plain", {"text/plain": {"schema": {}}}),
    ],
)
def test_stream_response_of_sequential_media_type(
    openapi_version: str, media_type: str, expected: dict[str, Any]
) -> None:
    @get("/", media_type=media_type)
    async def handler() -> Stream:
        raise NotImplementedError

    document = build_document(handler, openapi_version=openapi_version)

    assert document["paths"]["/"]["get"]["responses"]["200"]["content"] == expected


def _document_layered_parameter(handler: Any, parameters: dict[str, Any]) -> dict[str, Any]:
    document = build_document(Router("/", route_handlers=[handler], parameters=parameters))
    documented: list[dict[str, Any]] = document["paths"]["/"]["get"]["parameters"]
    (parameter,) = documented
    return parameter


def _document_and_serve(handler: Any, parameters: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    with create_test_client([Router("/", route_handlers=[handler], parameters=parameters)]) as client:
        return _document_layered_parameter(handler, parameters), client.get("/")


async def _provide_one() -> int:
    return 1


async def _provide_limit(limit: FromQuery[int] = 7) -> int:
    return limit


@get("/", dependencies={"one": Provide(_provide_one)}, sync_to_thread=False)
def _handler_with_default(one: NamedDependency[int], limit: FromQuery[int] = 5) -> int:
    return limit


@get("/", dependencies={"provided": Provide(_provide_limit)}, sync_to_thread=False)
def _handler_using_provider(provided: NamedDependency[int]) -> int:
    return provided


@get("/", sync_to_thread=False)
def _handler_without_parameter() -> int:
    return 1


@pytest.mark.parametrize(
    "handler, layer_required, required, default",
    [
        (_handler_with_default, None, False, 5),
        (_handler_with_default, False, False, 5),
        (_handler_with_default, True, True, 5),
        (_handler_using_provider, None, False, 7),
        (_handler_without_parameter, None, True, None),
        (_handler_without_parameter, False, False, None),
    ],
    ids=[
        "handler-default",
        "handler-default-layer-not-required",
        "handler-default-layer-required",
        "provider-default",
        "layer-only",
        "layer-only-not-required",
    ],
)
def test_layered_parameter_is_documented_as_the_server_reads_it(
    handler: Any, layer_required: bool | None, required: bool, default: int | None
) -> None:
    parameter, response = _document_and_serve(
        handler, {"limit": QueryParameter(annotation=int, required=layer_required)}
    )

    assert parameter["required"] is required
    assert parameter["schema"].get("default") == default
    assert response.status_code == (400 if required else 200)


def test_layered_header_parameter_documents_the_default_of_the_handler() -> None:
    @get("/", sync_to_thread=False)
    def handler(token: FromHeader[str] = "anon") -> str:
        return token

    parameter, response = _document_and_serve(handler, {"token": HeaderParameter(annotation=str, name="x-token")})

    assert parameter["name"] == "x-token"
    assert parameter["required"] is False
    assert parameter["schema"]["default"] == "anon"
    assert response.text == "anon"


def test_same_named_parameters_of_handler_and_dependency_at_different_locations_are_both_documented() -> None:
    async def provide_value(value: Annotated[int, HeaderParameter(name="x-value")]) -> int:
        return value

    @get("/", dependencies={"provided": Provide(provide_value)})
    async def handler(provided: NamedDependency[int], value: FromQuery[int]) -> None:
        return None

    parameters = build_document(handler)["paths"]["/"]["get"]["parameters"]

    assert [(parameter["name"], parameter["in"]) for parameter in parameters] == [
        ("value", "query"),
        ("x-value", "header"),
    ]


def test_parameters_of_dependency_used_twice_are_documented_once() -> None:
    async def provide_page(page_number: FromQuery[int] = 1) -> int:
        return page_number

    async def provide_offset(page: NamedDependency[int]) -> int:
        return page * 10

    async def provide_limit(page: NamedDependency[int]) -> int:
        return page + 10

    @get(
        "/",
        dependencies={
            "page": Provide(provide_page),
            "offset": Provide(provide_offset),
            "limit": Provide(provide_limit),
        },
    )
    async def handler(offset: NamedDependency[int], limit: NamedDependency[int]) -> None:
        return None

    parameters = build_document(handler, create_examples=True)["paths"]["/"]["get"]["parameters"]

    assert [parameter["name"] for parameter in parameters] == ["page_number"]
