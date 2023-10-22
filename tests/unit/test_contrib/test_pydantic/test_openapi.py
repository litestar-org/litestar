from datetime import date, timedelta
from decimal import Decimal
from types import ModuleType
from typing import Any, Callable, Dict, List, Pattern, Union, cast

import pydantic
import pytest
from pydantic import (
    BaseModel,
    Field,
    conbytes,
    condate,
    condecimal,
    confloat,
    conint,
    conlist,
    conset,
    constr,
)
from typing_extensions import Annotated

from litestar import Litestar, post
from litestar._openapi.schema_generation.constrained_fields import (
    create_date_constrained_field_schema,
    create_numerical_constrained_field_schema,
    create_string_constrained_field_schema,
)
from litestar._openapi.schema_generation.schema import SchemaCreator
from litestar.contrib.pydantic import PydanticPlugin, PydanticSchemaPlugin
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec import Example, Schema
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.params import KwargDefinition
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient, create_test_client
from litestar.typing import FieldDefinition
from litestar.utils import is_class_and_subclass
from tests.unit.test_contrib.test_pydantic.models import PydanticDataclassPerson, PydanticPerson

constr_kws: List[Dict[str, Any]] = [
    {"pattern": "^[a-zA-Z]$"},
    {"to_upper": True, "min_length": 1, "pattern": "^[a-zA-Z]$"},
    {"to_lower": True, "min_length": 1, "pattern": "^[a-zA-Z]$"},
    {"to_lower": True, "min_length": 10, "pattern": "^[a-zA-Z]$"},
    {"to_lower": True, "min_length": 10, "max_length": 100, "pattern": "^[a-zA-Z]$"},
    {"min_length": 1},
    {"min_length": 10},
    {"min_length": 10, "max_length": 100},
]

conlist_kws: List[Dict[str, Any]] = [
    {"min_length": 1},
    {"min_length": 1, "max_length": 10},
]

if pydantic.VERSION.startswith("1"):
    for kw in constr_kws:
        if "pattern" in kw:
            kw["regex"] = kw.pop("pattern")

    for kw in conlist_kws:
        if "max_length" in kw:
            kw["max_items"] = kw.pop("max_length")
        if "min_length" in kw:
            kw["min_items"] = kw.pop("min_length")

constrained_string = [
    *(constr(**kw) for kw in constr_kws),
    *[
        conbytes(min_length=1),
        conbytes(min_length=10),
        conbytes(min_length=10, max_length=100),
    ],
]

constrained_collection = [
    *(conlist(int, **kw) for kw in conlist_kws),
    *(conset(int, **kw) for kw in conlist_kws),
]

constrained_numbers = [
    conint(gt=10, lt=100),
    conint(ge=10, le=100),
    conint(ge=10, le=100, multiple_of=7),
    confloat(gt=10, lt=100),
    confloat(ge=10, le=100),
    confloat(ge=10, le=100, multiple_of=4.2),
    confloat(gt=10, lt=100, multiple_of=10),
    condecimal(gt=Decimal("10"), lt=Decimal("100")),
    condecimal(ge=Decimal("10"), le=Decimal("100")),
    condecimal(gt=Decimal("10"), lt=Decimal("100"), multiple_of=Decimal("5")),
    condecimal(ge=Decimal("10"), le=Decimal("100"), multiple_of=Decimal("2")),
]

constrained_dates = [
    condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
    condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
]


@pytest.mark.skipif(pydantic.VERSION.startswith("2"), reason="pydantic 1 specific logic")
@pytest.mark.parametrize("annotation", constrained_collection)
def test_create_collection_constrained_field_schema_pydantic_v1(annotation: Any) -> None:
    schema = SchemaCreator().for_collection_constrained_field(FieldDefinition.from_annotation(annotation))
    assert schema.type == OpenAPIType.ARRAY
    assert schema.items.type == OpenAPIType.INTEGER  # type: ignore[union-attr]
    assert schema.min_items == annotation.min_items
    assert schema.max_items == annotation.max_items


@pytest.mark.skipif(pydantic.VERSION.startswith("1"), reason="pydantic 2 specific logic")
@pytest.mark.parametrize("annotation", constrained_collection)
def test_create_collection_constrained_field_schema_pydantic_v2(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)
    schema = SchemaCreator().for_collection_constrained_field(field_definition)
    assert schema.type == OpenAPIType.ARRAY
    assert schema.items.type == OpenAPIType.INTEGER  # type: ignore[union-attr]
    assert any(getattr(m, "min_length", None) == schema.min_items for m in field_definition.metadata if m)
    assert any(getattr(m, "max_length", None) == schema.max_items for m in field_definition.metadata if m)


def test_create_collection_constrained_field_schema_sub_fields() -> None:
    for pydantic_fn in (conlist, conset):
        if pydantic.VERSION.startswith("1"):
            annotation = pydantic_fn(Union[str, int], min_items=1, max_items=10)  # type: ignore
        else:
            annotation = pydantic_fn(Union[str, int], min_length=1, max_length=10)  # type: ignore
        field_definition = FieldDefinition.from_annotation(annotation)
        schema = SchemaCreator().for_collection_constrained_field(field_definition)
        assert schema.type == OpenAPIType.ARRAY
        expected = {
            "items": {"oneOf": [{"type": "integer"}, {"type": "string"}]},
            "maxItems": 10,
            "minItems": 1,
            "type": "array",
        }
        if pydantic_fn == conset:
            # set should have uniqueItems always
            expected["uniqueItems"] = True

        assert schema.to_schema() == expected


@pytest.mark.skipif(pydantic.version.VERSION.startswith("2"), reason="pydantic 1 specific logic")
@pytest.mark.parametrize("annotation", constrained_string)
def test_create_string_constrained_field_schema_pydantic_v1(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_string_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert schema.type == OpenAPIType.STRING

    assert schema.min_length == annotation.min_length
    assert schema.max_length == annotation.max_length
    if pattern := getattr(annotation, "regex", None):
        assert schema.pattern == pattern.pattern if isinstance(pattern, Pattern) else pattern
    if annotation.to_lower:
        assert schema.description
    if annotation.to_upper:
        assert schema.description


@pytest.mark.skipif(pydantic.version.VERSION.startswith("1"), reason="pydantic 2 specific logic")
@pytest.mark.parametrize("annotation", constrained_string)
def test_create_string_constrained_field_schema_pydantic_v2(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_string_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert schema.type == OpenAPIType.STRING

    assert any(getattr(m, "min_length", None) == schema.min_length for m in field_definition.metadata if m)
    assert any(getattr(m, "max_length", None) == schema.max_length for m in field_definition.metadata if m)
    if pattern := getattr(annotation, "regex", getattr(annotation, "pattern", None)):
        assert schema.pattern == pattern.pattern if isinstance(pattern, Pattern) else pattern
    if any(getattr(m, "to_lower", getattr(m, "to_upper", None)) for m in field_definition.metadata if m):
        assert schema.description


@pytest.mark.skipif(pydantic.version.VERSION.startswith("2"), reason="pydantic 1 specific logic")
@pytest.mark.parametrize("annotation", constrained_numbers)
def test_create_numerical_constrained_field_schema_pydantic_v1(annotation: Any) -> None:
    from pydantic.types import ConstrainedDecimal, ConstrainedFloat, ConstrainedInt

    annotation = cast(Union[ConstrainedInt, ConstrainedFloat, ConstrainedDecimal], annotation)

    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_numerical_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert (
        schema.type == OpenAPIType.INTEGER if is_class_and_subclass(annotation, ConstrainedInt) else OpenAPIType.NUMBER
    )
    assert schema.exclusive_minimum == annotation.gt
    assert schema.minimum == annotation.ge
    assert schema.exclusive_maximum == annotation.lt
    assert schema.maximum == annotation.le
    assert schema.multiple_of == annotation.multiple_of


@pytest.mark.skipif(pydantic.version.VERSION.startswith("1"), reason="pydantic 2 specific logic")
@pytest.mark.parametrize("annotation", constrained_numbers)
def test_create_numerical_constrained_field_schema_pydantic_v2(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_numerical_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert schema.type == OpenAPIType.INTEGER if is_class_and_subclass(annotation, int) else OpenAPIType.NUMBER
    assert any(getattr(m, "gt", None) == schema.exclusive_minimum for m in field_definition.metadata if m)
    assert any(getattr(m, "ge", None) == schema.minimum for m in field_definition.metadata if m)
    assert any(getattr(m, "lt", None) == schema.exclusive_maximum for m in field_definition.metadata if m)
    assert any(getattr(m, "le", None) == schema.maximum for m in field_definition.metadata if m)
    assert any(getattr(m, "multiple_of", None) == schema.multiple_of for m in field_definition.metadata if m)


@pytest.mark.skipif(pydantic.version.VERSION.startswith("2"), reason="pydantic 1 specific logic")
@pytest.mark.parametrize("annotation", constrained_dates)
def test_create_date_constrained_field_schema_pydantic_v1(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_date_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert schema.type == OpenAPIType.STRING
    assert schema.format == OpenAPIFormat.DATE
    assert (date.fromtimestamp(schema.exclusive_minimum) if schema.exclusive_minimum else None) == annotation.gt
    assert (date.fromtimestamp(schema.minimum) if schema.minimum else None) == annotation.ge
    assert (date.fromtimestamp(schema.exclusive_maximum) if schema.exclusive_maximum else None) == annotation.lt
    assert (date.fromtimestamp(schema.maximum) if schema.maximum else None) == annotation.le


@pytest.mark.skipif(pydantic.version.VERSION.startswith("1"), reason="pydantic 2 specific logic")
@pytest.mark.parametrize("annotation", constrained_dates)
def test_create_date_constrained_field_schema_pydantic_v2(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_date_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert schema.type == OpenAPIType.STRING
    assert schema.format == OpenAPIFormat.DATE
    assert any(
        getattr(m, "gt", None) == (date.fromtimestamp(schema.exclusive_minimum) if schema.exclusive_minimum else None)
        for m in field_definition.metadata
        if m
    )
    assert any(
        getattr(m, "ge", None) == (date.fromtimestamp(schema.minimum) if schema.minimum else None)
        for m in field_definition.metadata
        if m
    )
    assert any(
        getattr(m, "lt", None) == (date.fromtimestamp(schema.exclusive_maximum) if schema.exclusive_maximum else None)
        for m in field_definition.metadata
        if m
    )
    assert any(
        getattr(m, "le", None) == (date.fromtimestamp(schema.maximum) if schema.maximum else None)
        for m in field_definition.metadata
        if m
    )


@pytest.mark.parametrize(
    "annotation", [*constrained_numbers, *constrained_collection, *constrained_string, *constrained_dates]
)
def test_create_constrained_field_schema(annotation: Any) -> None:
    schema = SchemaCreator().for_constrained_field(FieldDefinition.from_annotation(annotation))
    assert schema


@pytest.mark.parametrize("cls", (PydanticPerson, PydanticDataclassPerson))
def test_spec_generation(cls: Any) -> None:
    @post("/")
    def handler(data: cls) -> cls:
        return data

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema

        assert schema.to_schema()["components"]["schemas"][cls.__name__] == {
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "id": {"type": "string"},
                "optional": {"oneOf": [{"type": "null"}, {"type": "string"}]},
                "complex": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                },
                "pets": {
                    "oneOf": [
                        {"type": "null"},
                        {"items": {"$ref": "#/components/schemas/DataclassPet"}, "type": "array"},
                    ]
                },
            },
            "type": "object",
            "required": ["complex", "first_name", "id", "last_name"],
            "title": f"{cls.__name__}",
        }


@pytest.mark.parametrize("create_examples", (True, False))
def test_schema_generation(create_examples: bool) -> None:
    class Lookup(BaseModel):
        if pydantic.VERSION.startswith("1"):
            id: Annotated[
                str,
                Field(
                    min_length=12,
                    max_length=16,
                    description="A unique identifier",
                    example="e4eaaaf2-d142-11e1-b3e4-080027620cdd",  # pyright: ignore
                ),
            ]
        else:
            id: Annotated[  # type: ignore[no-redef]
                str,
                Field(
                    min_length=12,
                    max_length=16,
                    description="A unique identifier",
                    json_schema_extra={"example": "e4eaaaf2-d142-11e1-b3e4-080027620cdd"},
                ),
            ]

    @post("/example")
    async def example_route() -> Lookup:
        return Lookup(id="1234567812345678")

    with create_test_client(
        route_handlers=[example_route],
        openapi_config=OpenAPIConfig(
            title="Example API",
            version="1.0.0",
            create_examples=create_examples,
        ),
        signature_namespace={"Lookup": Lookup},
    ) as client:
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_200_OK
        assert response.json()["components"]["schemas"]["Lookup"]["properties"]["id"] == {
            "description": "A unique identifier",
            "examples": [{"value": "e4eaaaf2-d142-11e1-b3e4-080027620cdd"}],
            "maxLength": 16,
            "minLength": 12,
            "type": "string",
        }


def test_schema_by_alias() -> None:
    class RequestWithAlias(BaseModel):
        first: str = Field(alias="second")

    class ResponseWithAlias(BaseModel):
        first: str = Field(alias="second")

    @post("/", signature_types=[RequestWithAlias, ResponseWithAlias])
    def handler(data: RequestWithAlias) -> ResponseWithAlias:
        return ResponseWithAlias(second=data.first)

    app = Litestar(route_handlers=[handler], openapi_config=OpenAPIConfig(title="my title", version="1.0.0"))

    assert app.openapi_schema
    schemas = app.openapi_schema.to_schema()["components"]["schemas"]
    request_key = "second"
    assert schemas["RequestWithAlias"] == {
        "properties": {request_key: {"type": "string"}},
        "type": "object",
        "required": [request_key],
        "title": "RequestWithAlias",
    }
    response_key = "first"
    assert schemas["ResponseWithAlias"] == {
        "properties": {response_key: {"type": "string"}},
        "type": "object",
        "required": [response_key],
        "title": "ResponseWithAlias",
    }

    with TestClient(app) as client:
        response = client.post("/", json={request_key: "foo"})
        assert response.json() == {response_key: "foo"}


def test_schema_by_alias_plugin_override() -> None:
    class RequestWithAlias(BaseModel):
        first: str = Field(alias="second")

    class ResponseWithAlias(BaseModel):
        first: str = Field(alias="second")

    @post("/", signature_types=[RequestWithAlias, ResponseWithAlias])
    def handler(data: RequestWithAlias) -> ResponseWithAlias:
        return ResponseWithAlias(second=data.first)

    app = Litestar(
        route_handlers=[handler],
        openapi_config=OpenAPIConfig(title="my title", version="1.0.0"),
        plugins=[PydanticPlugin(prefer_alias=True)],
    )

    assert app.openapi_schema
    schemas = app.openapi_schema.to_schema()["components"]["schemas"]
    request_key = "second"
    assert schemas["RequestWithAlias"] == {
        "properties": {request_key: {"type": "string"}},
        "type": "object",
        "required": [request_key],
        "title": "RequestWithAlias",
    }
    response_key = "second"
    assert schemas["ResponseWithAlias"] == {
        "properties": {response_key: {"type": "string"}},
        "type": "object",
        "required": [response_key],
        "title": "ResponseWithAlias",
    }

    with TestClient(app) as client:
        response = client.post("/", json={request_key: "foo"})
        assert response.json() == {response_key: "foo"}


def test_create_schema_for_field() -> None:
    class Model(BaseModel):
        if pydantic.VERSION.startswith("1"):
            value: str = Field(
                title="title", description="description", example="example", max_length=16  # pyright: ignore
            )
        else:
            value: str = Field(  # type: ignore[no-redef]
                title="title", description="description", max_length=16, json_schema_extra={"example": "example"}
            )

    schemas: Dict[str, Schema] = {}
    field_definition = FieldDefinition.from_kwarg(name="Model", annotation=Model)
    SchemaCreator(schemas=schemas, plugins=[PydanticSchemaPlugin()]).for_field_definition(field_definition)
    schema = schemas["Model"]

    assert schema.properties["value"].description == "description"  # type: ignore
    assert schema.properties["value"].title == "title"  # type: ignore
    assert schema.properties["value"].examples == [Example(value="example")]  # type: ignore


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_create_schema_for_pydantic_model_with_annotated_model_attribute(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]"
) -> None:
    """Test that a model with an annotated attribute is correctly handled."""
    module = create_module(
        f"""
{'from __future__ import annotations' if with_future_annotations else ''}
from typing_extensions import Annotated
from pydantic import BaseModel

class Foo(BaseModel):
    foo: Annotated[int, "Foo description"]
"""
    )
    schemas: Dict[str, Schema] = {}
    SchemaCreator(schemas=schemas, plugins=[PydanticSchemaPlugin()]).for_field_definition(
        FieldDefinition.from_annotation(module.Foo)
    )
    schema = schemas["Foo"]
    assert schema.properties and "foo" in schema.properties
