import json
from collections.abc import Callable
from dataclasses import dataclass, make_dataclass
from enum import Enum
from itertools import permutations
from types import ModuleType
from typing import Annotated, Any, Generic, Optional, TypeVar

import msgspec
import pytest
from pydantic import BaseModel, EmailStr, RootModel, create_model

from litestar import get, post
from litestar._openapi.schema_generation import SchemaCreator
from litestar.dto import DataclassDTO, DTOConfig
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import Example, Reference, Schema
from litestar.params import Body, FromQuery, JSONBody, KwargDefinition, QueryParameter
from litestar.plugins.pydantic import PydanticSchemaPlugin
from litestar.typing import FieldDefinition
from tests.unit.test_openapi.utils import build_document


class Color(Enum):
    RED = "red"
    BLUE = "blue"


@dataclass
class Item:
    name: str
    color: Color = Color.RED
    accent: Annotated[Color, KwargDefinition(description="accent colour")] = Color.BLUE


class Inner(BaseModel):
    x: int = 1


class Wrapper(RootModel[Inner]):
    pass


def test_document_does_not_depend_on_handler_registration_order() -> None:
    @get("/encoded", content_encoding="base64", content_media_type="image/png", sync_to_thread=False)
    def encoded() -> Item:
        raise NotImplementedError

    @get("/plain", sync_to_thread=False)
    def plain(color: Annotated[Color, QueryParameter(description="filter by colour")]) -> Item:
        raise NotImplementedError

    @post("/create", sync_to_thread=False)
    def create(data: Annotated[Item, Body(description="the item to create", title="New item")]) -> list[Item]:
        raise NotImplementedError

    documents = [build_document(*handlers) for handlers in permutations([encoded, plain, create])]

    encoded_documents = {msgspec.json.encode(document, order="deterministic") for document in documents}
    assert len(encoded_documents) == 1
    component = documents[0]["components"]["schemas"]["Item"]
    assert "contentEncoding" not in component
    assert "contentMediaType" not in component
    assert _response_schema(documents[0], "/plain") == {"$ref": "#/components/schemas/Item"}
    assert _response_schema(documents[0], "/encoded") == {
        "allOf": [{"$ref": "#/components/schemas/Item"}],
        "contentEncoding": "base64",
        "contentMediaType": "image/png",
    }


def test_field_metadata_is_not_written_to_shared_enum_component() -> None:
    @get("/", sync_to_thread=False)
    def handler() -> Item:
        raise NotImplementedError

    document = build_document(handler)

    assert document["components"]["schemas"]["Color"] == {"type": "string", "enum": ["red", "blue"], "title": "Color"}
    assert document["components"]["schemas"]["Item"]["properties"] == {
        "name": {"type": "string"},
        "color": {"allOf": [{"$ref": "#/components/schemas/Color"}], "default": "red"},
        "accent": {
            "allOf": [{"$ref": "#/components/schemas/Color"}],
            "description": "accent colour",
            "default": "blue",
        },
    }


def test_field_metadata_is_not_written_to_shared_model_component() -> None:
    @post("/first", sync_to_thread=False)
    def first(data: Annotated[Item, Body(description="first usage")]) -> None:
        return None

    @post("/second", sync_to_thread=False)
    def second(data: Annotated[Item, Body(description="second usage")]) -> None:
        return None

    document = build_document(first, second)

    assert "description" not in document["components"]["schemas"]["Item"]
    for path, description in (("/first", "first usage"), ("/second", "second usage")):
        assert document["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"] == {
            "allOf": [{"$ref": "#/components/schemas/Item"}],
            "description": description,
        }


def test_component_key_on_root_model_does_not_write_to_root_type_component() -> None:
    @post("/wrapped", sync_to_thread=False)
    def wrapped(data: Annotated[Wrapper, Body(schema_component_key="WrapperKey", description="wrapped")]) -> None:
        return None

    @post("/inner", sync_to_thread=False)
    def inner(data: JSONBody[Inner]) -> None:
        return None

    document = build_document(wrapped, inner)

    assert "description" not in document["components"]["schemas"]["Inner"]
    assert document["paths"]["/wrapped"]["post"]["requestBody"]["content"]["application/json"]["schema"] == {
        "allOf": [{"$ref": "#/components/schemas/Inner"}],
        "description": "wrapped",
    }


@get("/single-color", sync_to_thread=False)
def single_color(color: FromQuery[Color]) -> None:
    return None


@get("/many-colors", sync_to_thread=False)
def many_colors(colors: Annotated[list[Color], QueryParameter(min_items=1)]) -> None:
    return None


@get("/single-item", sync_to_thread=False)
def single_item() -> Item:
    raise NotImplementedError


@post("/many-items", sync_to_thread=False)
def many_items(data: Annotated[list[Item], Body(min_items=1)]) -> None:
    return None


@pytest.mark.parametrize(
    "single, many, component",
    [(single_color, many_colors, "Color"), (single_item, many_items, "Item")],
    ids=["enum", "model"],
)
def test_component_examples_do_not_depend_on_handler_registration_order(
    single: HTTPRouteHandler, many: HTTPRouteHandler, component: str
) -> None:
    for handlers in ((single, many), (many, single)):
        document = build_document(*handlers, create_examples=True)
        assert document["components"]["schemas"][component]["examples"]


def test_optional_reference_documents_default_once() -> None:
    @get("/", sync_to_thread=False)
    def handler(color: FromQuery[Optional[Color]] = Color.RED) -> None:
        return None

    document = build_document(handler)

    assert document["paths"]["/"]["get"]["parameters"][0]["schema"] == {
        "oneOf": [{"$ref": "#/components/schemas/Color"}, {"type": "null"}],
        "default": "red",
    }


def test_process_schema_result_leaves_component_schema_untouched() -> None:
    creator = SchemaCreator(plugins=[PydanticSchemaPlugin()])
    component = creator.for_plugin(FieldDefinition.from_annotation(Inner), creator.plugins[0])  # type: ignore[index]
    assert isinstance(component, Schema)

    result = creator.process_schema_result(
        FieldDefinition.from_annotation(Inner, kwarg_definition=KwargDefinition(description="one usage")), component
    )

    assert component.description is None
    assert isinstance(result, Schema)
    assert result.description == "one usage"
    assert result.all_of
    assert isinstance(result.all_of[0], Reference)


def test_component_name_colliding_with_disambiguated_name() -> None:
    @dataclass
    class Other:
        value: int

    def name_creator(field_definition: FieldDefinition) -> str:
        return "Model" if field_definition.annotation in (Item, Inner) else field_definition.annotation.__name__

    @post("/item", sync_to_thread=False)
    def item(data: JSONBody[Item]) -> None:
        return None

    @post("/inner", sync_to_thread=False)
    def inner(data: JSONBody[Inner]) -> None:
        return None

    @post("/keyed", sync_to_thread=False)
    def keyed(data: Annotated[Other, Body(schema_component_key="Item")]) -> None:
        return None

    for handlers in ((keyed, item, inner), (item, inner, keyed)):
        document = build_document(*handlers, schema_component_name_creator=name_creator)
        schemas = document["components"]["schemas"]
        assert len(schemas) == 4
        for path, title in (("/keyed", "Other"), ("/item", "Item"), ("/inner", "Inner")):
            ref = document["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
            assert schemas[ref.removeprefix("#/components/schemas/")]["title"].endswith(title)


def test_parametrized_pydantic_generics_of_same_named_types(create_module: Callable[[str], ModuleType]) -> None:
    first = create_module("""
from dataclasses import dataclass

@dataclass
class Thing:
    first: int
""")
    second = create_module("""
from dataclasses import dataclass

@dataclass
class Thing:
    second: str
""")
    module = create_module("""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class Envelope(BaseModel, Generic[T]):
    value: T
""")

    @post("/", sync_to_thread=False)
    def handler(data: JSONBody[module.Envelope[first.Thing]]) -> module.Envelope[second.Thing]:  # type: ignore[name-defined]
        raise NotImplementedError

    @get("/numbers", sync_to_thread=False)
    def numbers() -> module.Envelope[int]:  # type: ignore[name-defined]
        raise NotImplementedError

    document = build_document(handler, numbers)
    schemas = document["components"]["schemas"]

    assert "Envelope_int" in schemas
    request_ref = document["paths"]["/"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    response_ref = document["paths"]["/"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
    assert request_ref != response_ref
    request_value = schemas[request_ref.removeprefix("#/components/schemas/")]["properties"]["value"]["$ref"]
    response_value = schemas[response_ref.removeprefix("#/components/schemas/")]["properties"]["value"]["$ref"]
    assert "first" in schemas[request_value.removeprefix("#/components/schemas/")]["properties"]
    assert "second" in schemas[response_value.removeprefix("#/components/schemas/")]["properties"]


def test_field_metadata_is_not_written_to_schema_shared_by_plugin() -> None:
    @get("/described", sync_to_thread=False)
    def described(email: Annotated[EmailStr, QueryParameter(description="first usage")]) -> None:
        return None

    @get("/plain", sync_to_thread=False)
    def plain(email: FromQuery[EmailStr]) -> None:
        return None

    document = build_document(described, plain)

    assert document["paths"]["/described"]["get"]["parameters"][0]["schema"]["description"] == "first usage"
    assert "description" not in document["paths"]["/plain"]["get"]["parameters"][0]["schema"]


def test_response_spec_does_not_generate_component_examples_unless_enabled_on_config() -> None:
    @get("/spec", responses={404: ResponseSpec(Item)}, sync_to_thread=False)
    def spec() -> None:
        return None

    @get("/item", sync_to_thread=False)
    def item() -> Item:
        raise NotImplementedError

    for handlers in ((spec, item), (item, spec)):
        assert "examples" not in build_document(*handlers)["components"]["schemas"]["Item"]
        assert "examples" in build_document(*handlers, create_examples=True)["components"]["schemas"]["Item"]


T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    items: list[T]


@dataclass
class ItemHolder:
    item: Item
    optional_item: Optional[Item]
    described_item: Annotated[Item, KwargDefinition(description="described")]
    page: Page[Item]


@dataclass
class Account:
    name: str
    secret: str
    owner: Item


class AccountDTO(DataclassDTO[Account]):
    __schema_name__ = "PublicAccount"
    config = DTOConfig(exclude={"secret"})


def _make_dataclass(name: str, **fields: Any) -> Any:
    return make_dataclass(name, list(fields.items()))


def _make_struct(name: str, **fields: Any) -> Any:
    return msgspec.defstruct(name, list(fields.items()))


def _make_pydantic_model(name: str, **fields: Any) -> Any:
    field_definitions: dict[str, Any] = {field_name: (field_type, ...) for field_name, field_type in fields.items()}
    return create_model(name, **field_definitions)


def _make_enum(name: str, **members: Any) -> Any:
    enum_type: Any = Enum
    return enum_type(name, members)


def _subscript(origin: Any, *arguments: Any) -> Any:
    return origin[arguments[0] if len(arguments) == 1 else arguments]


def _returning(path: str, annotation: Any) -> HTTPRouteHandler:
    def handler() -> Any:
        raise NotImplementedError

    handler.__annotations__["return"] = annotation
    return get(path, sync_to_thread=False)(handler)


def _resolve(document: dict[str, Any], schema: dict[str, Any]) -> Any:
    return document["components"]["schemas"][schema["$ref"].removeprefix("#/components/schemas/")]


def _response_schema(document: dict[str, Any], path: str) -> Any:
    return document["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]


def _inline(document: dict[str, Any], schema: Any) -> Any:
    if isinstance(schema, dict):
        if "$ref" in schema:
            return _inline(document, _resolve(document, schema))
        return {key: _inline(document, value) for key, value in schema.items()}
    if isinstance(schema, list):
        return [_inline(document, value) for value in schema]
    return schema


def _component_contents(document: dict[str, Any]) -> list[str]:
    return sorted(
        json.dumps(_inline(document, schema), sort_keys=True) for schema in document["components"]["schemas"].values()
    )


@pytest.mark.parametrize("make_model", [_make_dataclass, _make_struct, _make_pydantic_model])
def test_same_named_classes_get_distinct_components(make_model: Any) -> None:
    first = _returning("/first", make_model("Thing", first=int))
    second = _returning("/second", make_model("Thing", second=str))

    documents = [build_document(*handlers) for handlers in ((first, second), (second, first))]

    for document, registered_first in zip(documents, ("/first", "/second")):
        assert list(document["components"]["schemas"]) == ["Thing", "Thing_2"]
        assert _response_schema(document, registered_first) == {"$ref": "#/components/schemas/Thing"}
        for path in ("first", "second"):
            assert list(_resolve(document, _response_schema(document, f"/{path}"))["properties"]) == [path]
    assert _component_contents(documents[0]) == _component_contents(documents[1])


def test_same_named_enum_and_model_get_distinct_components() -> None:
    kind = _make_enum("Thing", A="a")
    thing = _make_dataclass("Thing", value=int)

    document = build_document(_returning("/", _make_dataclass("Holder", kind=kind, thing=thing)))

    properties = document["components"]["schemas"]["Holder"]["properties"]
    assert len(document["components"]["schemas"]) == 3
    assert _resolve(document, properties["kind"])["enum"] == ["a"]
    assert _resolve(document, properties["thing"])["properties"] == {"value": {"type": "integer"}}


def test_same_named_models_nesting_different_same_named_classes_stay_distinct() -> None:
    first = _returning("/first", _make_dataclass("Outer", node=_make_dataclass("Node", first=int)))
    second = _returning("/second", _make_dataclass("Outer", node=_make_dataclass("Node", second=str)))

    documents = [build_document(*handlers) for handlers in ((first, second), (second, first))]

    for document in documents:
        assert list(document["components"]["schemas"]) == ["Node", "Node_2", "Outer", "Outer_2"]
        for path in ("first", "second"):
            outer = _resolve(document, _response_schema(document, f"/{path}"))
            assert list(_resolve(document, outer["properties"]["node"])["properties"]) == [path]
    assert _component_contents(documents[0]) == _component_contents(documents[1])


def test_same_named_type_arguments_get_distinct_generic_components() -> None:
    first = _returning("/first", _subscript(Page, _make_dataclass("Thing", first=int)))
    second = _returning("/second", _subscript(Page, _make_dataclass("Thing", second=str)))

    document = build_document(first, second)

    assert list(document["components"]["schemas"]) == ["Page_Thing", "Page_Thing_2", "Thing", "Thing_2"]
    for path in ("first", "second"):
        page = _resolve(document, _response_schema(document, f"/{path}"))
        assert list(_resolve(document, page["properties"]["items"]["items"])["properties"]) == [path]


def test_numbered_component_name_skips_names_in_use() -> None:
    first = _returning("/first", _make_dataclass("Thing", first=int))
    second = _returning("/second", _make_dataclass("Thing", second=str))
    third = _returning("/third", _make_dataclass("Thing_2", third=int))

    document = build_document(first, second, third)

    assert list(document["components"]["schemas"]) == ["Thing", "Thing_2", "Thing_3"]
    for path in ("first", "second", "third"):
        assert list(_resolve(document, _response_schema(document, f"/{path}"))["properties"]) == [path]


def test_classes_made_per_handler_with_equal_schemas_share_one_component() -> None:
    def make_page() -> Any:
        return _make_dataclass("ItemPage", items=list[Item], total=int)

    def make_tree() -> Any:
        tree = create_model("Tree", children=(_subscript(list, "Tree"), ...))
        tree.model_rebuild(_types_namespace={"Tree": tree})
        return tree

    body = Body(schema_component_key="Keyed")
    handlers = [
        *(_returning(f"/page/{index}", make_page()) for index in range(3)),
        *(_returning(f"/tree/{index}", make_tree()) for index in range(2)),
        *(_returning(f"/keyed/{index}", _subscript(Annotated, make_page(), body)) for index in range(2)),
    ]

    documents = [build_document(*ordered) for ordered in (handlers, handlers[::-1])]

    with_examples = build_document(*handlers, create_examples=True)
    for document in (*documents, with_examples):
        assert list(document["components"]["schemas"]) == ["Color", "Item", "ItemPage", "Keyed", "Tree"]
        for path, name in (("/page/2", "ItemPage"), ("/tree/1", "Tree"), ("/keyed/1", "Keyed")):
            assert _response_schema(document, path) == {"$ref": f"#/components/schemas/{name}"}
        tree = document["components"]["schemas"]["Tree"]
        assert tree["properties"]["children"]["items"] == {"$ref": "#/components/schemas/Tree"}
    assert documents[0] == documents[1]


def test_same_named_classes_differing_in_their_examples_get_distinct_components() -> None:
    def make_thing(value: int) -> Any:
        return _make_dataclass(
            "Thing", value=_subscript(Annotated, int, KwargDefinition(examples=[Example(value=value)]))
        )

    document = build_document(_returning("/first", make_thing(1)), _returning("/second", make_thing(2)))

    assert list(document["components"]["schemas"]) == ["Thing", "Thing_2"]
    for path, value in (("/first", 1), ("/second", 2)):
        thing = _resolve(document, _response_schema(document, path))
        assert thing["properties"]["value"]["examples"] == [value]


def test_equal_same_named_classes_nesting_equal_same_named_classes_share_components() -> None:
    def make_outer() -> Any:
        return _make_dataclass("Outer", node=_make_dataclass("Node", value=int))

    document = build_document(_returning("/first", make_outer()), _returning("/second", make_outer()))

    assert list(document["components"]["schemas"]) == ["Node", "Outer"]
    assert document["components"]["schemas"]["Outer"] == {
        "type": "object",
        "properties": {"node": {"$ref": "#/components/schemas/Node"}},
        "required": ["node"],
        "title": "Outer",
    }
    assert _response_schema(document, "/first") == _response_schema(document, "/second")
    assert _response_schema(document, "/first") == {"$ref": "#/components/schemas/Outer"}


def test_component_name_clash_after_fallback_raises() -> None:
    first = _returning("/first", msgspec.defstruct("Thing", [("first", int)], module="alpha"))
    second = _returning("/second", msgspec.defstruct("Thing", [("second", int)], module="beta"))
    third = _returning("/third", msgspec.defstruct("alpha_Thing", [("third", int)], module="gamma"))

    with pytest.raises(ImproperlyConfiguredException, match="Schema component names must be unique"):
        build_document(first, second, third)


def test_name_creator_names_same_named_classes() -> None:
    first_model = _make_dataclass("Thing", first=int)
    second_model = _make_dataclass("Thing", second=str)

    def name_creator(field_definition: FieldDefinition) -> str:
        return "FirstThing" if field_definition.annotation is first_model else "SecondThing"

    document = build_document(
        _returning("/second", second_model),
        _returning("/first", first_model),
        schema_component_name_creator=name_creator,
    )

    assert _response_schema(document, "/first") == {"$ref": "#/components/schemas/FirstThing"}
    assert _response_schema(document, "/second") == {"$ref": "#/components/schemas/SecondThing"}
    assert list(document["components"]["schemas"]["FirstThing"]["properties"]) == ["first"]


def test_same_named_classes_sharing_a_component_key_raise() -> None:
    body = Body(schema_component_key="Shared")
    first = _returning("/first", _subscript(Annotated, _make_dataclass("Thing", first=int), body))
    second = _returning("/second", _subscript(Annotated, _make_dataclass("Thing", second=str), body))

    with pytest.raises(ImproperlyConfiguredException, match="Schema component keys must be unique"):
        build_document(first, second)


def test_one_class_used_in_many_places_yields_one_component() -> None:
    @get("/item", sync_to_thread=False)
    def item(color: Annotated[Color, QueryParameter(description="filter by colour")]) -> Item:
        raise NotImplementedError

    @get("/optional", sync_to_thread=False)
    def optional() -> Optional[Item]:
        raise NotImplementedError

    @get("/page", sync_to_thread=False)
    def page() -> Page[Item]:
        raise NotImplementedError

    @get("/other-page", sync_to_thread=False)
    def other_page() -> Annotated[Page[Item], KwargDefinition(description="another page")]:
        raise NotImplementedError

    @post("/create", sync_to_thread=False)
    def create(data: Annotated[Item, Body(description="the item to create")]) -> list[Item]:
        raise NotImplementedError

    @post("/replace", sync_to_thread=False)
    def replace(data: JSONBody[Item]) -> ItemHolder:
        raise NotImplementedError

    document = build_document(item, optional, page, other_page, create, replace)

    assert list(document["components"]["schemas"]) == ["Color", "Item", "ItemHolder", "Page_Item"]


def test_dto_schema_name_shared_by_handlers_yields_one_component() -> None:
    @get("/first", return_dto=AccountDTO, sync_to_thread=False)
    def first() -> Account:
        raise NotImplementedError

    @get("/second", return_dto=AccountDTO, sync_to_thread=False)
    def second() -> Account:
        raise NotImplementedError

    @get("/page", return_dto=AccountDTO, sync_to_thread=False)
    def page() -> Page[Account]:
        raise NotImplementedError

    @get("/other-page", return_dto=AccountDTO, sync_to_thread=False)
    def other_page() -> Page[Account]:
        raise NotImplementedError

    document = build_document(first, second, page, other_page)

    schemas = document["components"]["schemas"]
    assert [name for name in schemas if "PublicAccount" in name] == ["Page_PublicAccount", "PublicAccount"]
    assert _response_schema(document, "/first") == _response_schema(document, "/second")
    assert _response_schema(document, "/page") == _response_schema(document, "/other-page")
