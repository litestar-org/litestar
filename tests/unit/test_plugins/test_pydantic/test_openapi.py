import copy
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal
from types import ModuleType
from typing import Annotated, Any, Generic, Optional, TypeVar, Union

import annotated_types
import pydantic as pydantic_v2
import pytest
from pydantic.alias_generators import to_camel

from litestar import Litestar, get, post
from litestar._openapi.schema_generation.schema import SchemaCreator
from litestar.di import NamedDependency, Provide
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec import Reference, Schema
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.params import FromQuery, JSONBody
from litestar.plugins.pydantic import PydanticDTO, PydanticPlugin, PydanticSchemaPlugin
from litestar.testing import TestClient, create_test_client
from litestar.typing import FieldDefinition
from litestar.utils import is_class_and_subclass
from tests.helpers import get_schema_for_field_definition
from tests.unit.test_openapi.utils import request_body_component
from tests.unit.test_plugins.test_pydantic.models import (
    PydanticDataclassPerson,
    PydanticPerson,
)

from . import PydanticVersion

T = TypeVar("T")

AnyBaseModelType = type[pydantic_v2.BaseModel]


constrained_string_v2 = [
    pydantic_v2.constr(pattern="^[a-zA-Z]$"),
    pydantic_v2.constr(to_upper=True, min_length=1, pattern="^[a-zA-Z]$"),
    pydantic_v2.constr(to_lower=True, min_length=1, pattern="^[a-zA-Z]$"),
    pydantic_v2.constr(to_lower=True, min_length=10, pattern="^[a-zA-Z]$"),
    pydantic_v2.constr(to_lower=True, min_length=10, max_length=100, pattern="^[a-zA-Z]$"),
    pydantic_v2.constr(min_length=1),
    pydantic_v2.constr(min_length=10),
    pydantic_v2.constr(min_length=10, max_length=100),
]

constrained_bytes_v2 = [
    pydantic_v2.conbytes(min_length=1),
    pydantic_v2.conbytes(min_length=10),
    pydantic_v2.conbytes(min_length=10, max_length=100),
]


constrained_collection_v2 = [
    pydantic_v2.conlist(int, min_length=1),
    pydantic_v2.conlist(int, min_length=1, max_length=10),
    pydantic_v2.conset(int, min_length=1),
    pydantic_v2.conset(int, min_length=1, max_length=10),
]


constrained_numbers_v2 = [
    pydantic_v2.conint(gt=10, lt=100),
    pydantic_v2.conint(ge=10, le=100),
    pydantic_v2.conint(ge=10, le=100, multiple_of=7),
    pydantic_v2.confloat(gt=10, lt=100),
    pydantic_v2.confloat(ge=10, le=100),
    pydantic_v2.confloat(ge=10, le=100, multiple_of=4.2),
    pydantic_v2.confloat(gt=10, lt=100, multiple_of=10),
    pydantic_v2.condecimal(gt=Decimal("10"), lt=Decimal("100")),
    pydantic_v2.condecimal(ge=Decimal("10"), le=Decimal("100")),
    pydantic_v2.condecimal(gt=Decimal("10"), lt=Decimal("100"), multiple_of=Decimal("5")),
    pydantic_v2.condecimal(ge=Decimal("10"), le=Decimal("100"), multiple_of=Decimal("2")),
]


constrained_dates_v2 = [
    pydantic_v2.condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    pydantic_v2.condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
    pydantic_v2.condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    pydantic_v2.condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
]


@pytest.fixture()
def schema_creator(plugin: PydanticSchemaPlugin) -> SchemaCreator:
    return SchemaCreator(plugins=[plugin])


@pytest.fixture()
def plugin() -> PydanticSchemaPlugin:
    return PydanticSchemaPlugin()


@pytest.mark.parametrize("make_constraint", [pydantic_v2.conlist, pydantic_v2.conset, pydantic_v2.confrozenset])
@pytest.mark.parametrize(
    "min_length, max_length",
    [
        (None, None),
        (1, None),
        (1, 1),
        (None, 1),
    ],
)
def test_create_collection_constrained_field_schema_pydantic_v2(
    make_constraint: Callable[..., Any],
    min_length: Optional[int],
    max_length: Optional[int],
    schema_creator: SchemaCreator,
    plugin: PydanticSchemaPlugin,
) -> None:
    class Model(pydantic_v2.BaseModel):
        field: make_constraint(int, min_length=min_length, max_length=max_length)  # type: ignore[valid-type]

    schema = schema_creator.for_plugin(FieldDefinition.from_annotation(Model), plugin).properties["field"]  # pyright: ignore[reportAttributeAccessIssue]

    assert schema.type == OpenAPIType.ARRAY  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.items.type == OpenAPIType.INTEGER
    assert schema.min_items == min_length  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.max_items == max_length  # pyright: ignore[reportAttributeAccessIssue]


@pytest.fixture()
def conset(pydantic_version: PydanticVersion) -> Any:
    return pydantic_v2.conset


@pytest.fixture()
def conlist(pydantic_version: PydanticVersion) -> Any:
    return pydantic_v2.conlist


def test_create_collection_constrained_field_schema_sub_fields(
    pydantic_version: PydanticVersion,
    conset: Any,
    conlist: Any,
    schema_creator: SchemaCreator,
    plugin: PydanticSchemaPlugin,
) -> None:
    class Modelv2(pydantic_v2.BaseModel):
        set_field: conset(Union[str, int], min_length=1, max_length=10)  # type: ignore[valid-type]
        list_field: conlist(Union[str, int], min_length=1, max_length=10)  # type: ignore[valid-type]

    model_schema = schema_creator.for_plugin(FieldDefinition.from_annotation(Modelv2), plugin)

    def _get_schema_type(s: Any) -> OpenAPIType:
        assert isinstance(s, Schema)
        assert isinstance(s.type, OpenAPIType)
        return s.type

    for field_name in ["set_field", "list_field"]:
        schema = model_schema.properties[field_name]  # pyright: ignore[reportAttributeAccessIssue]

        assert schema.type == OpenAPIType.ARRAY  # pyright: ignore[reportAttributeAccessIssue]
        assert schema.max_items == 10  # pyright: ignore[reportAttributeAccessIssue]
        assert schema.min_items == 1  # pyright: ignore[reportAttributeAccessIssue]
        assert isinstance(schema.items, Schema)  # pyright: ignore[reportAttributeAccessIssue]
        assert schema.items.one_of is not None  # pyright: ignore[reportAttributeAccessIssue]

        # https://github.com/litestar-org/litestar/pull/2570#issuecomment-1788122570
        assert {_get_schema_type(s) for s in schema.items.one_of} == {OpenAPIType.STRING, OpenAPIType.INTEGER}  # pyright: ignore[reportAttributeAccessIssue]

    # set should have uniqueItems always
    assert model_schema.properties["set_field"].unique_items  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("annotation", constrained_string_v2)
def test_create_string_constrained_field_schema_pydantic_v2(
    annotation: Any,
    schema_creator: SchemaCreator,
    plugin: PydanticSchemaPlugin,
) -> None:
    constraint: pydantic_v2.types.StringConstraints = annotation.__metadata__[0]

    class Model(pydantic_v2.BaseModel):
        field: annotation

    schema = schema_creator.for_plugin(FieldDefinition.from_annotation(Model), plugin).properties["field"]  # pyright: ignore[reportAttributeAccessIssue]

    assert schema.type == OpenAPIType.STRING  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.min_length == constraint.min_length  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.max_length == constraint.max_length  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.pattern == constraint.pattern  # pyright: ignore[reportAttributeAccessIssue]
    if constraint.to_upper:
        assert schema.description == "must be in upper case"
    if constraint.to_lower:
        assert schema.description == "must be in lower case"


@pytest.mark.parametrize("annotation", constrained_bytes_v2)
def test_create_byte_constrained_field_schema_pydantic_v2(
    annotation: Any,
    schema_creator: SchemaCreator,
    plugin: PydanticSchemaPlugin,
) -> None:
    constraint: annotated_types.Len = annotation.__metadata__[1]

    class Model(pydantic_v2.BaseModel):
        field: annotation

    schema = schema_creator.for_plugin(FieldDefinition.from_annotation(Model), plugin).properties["field"]  # pyright: ignore[reportAttributeAccessIssue]

    assert schema.type == OpenAPIType.STRING  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.min_length == constraint.min_length  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.max_length == constraint.max_length  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    "make_constraint, constraint_kwargs",
    [
        (pydantic_v2.conint, {"gt": 10, "lt": 100}),
        (pydantic_v2.conint, {"ge": 10, "le": 100}),
        (pydantic_v2.conint, {"ge": 10, "le": 100, "multiple_of": 7}),
        (pydantic_v2.confloat, {"gt": 10, "lt": 100}),
        (pydantic_v2.confloat, {"ge": 10, "le": 100}),
        (pydantic_v2.confloat, {"ge": 10, "le": 100, "multiple_of": 4.2}),
        (pydantic_v2.confloat, {"gt": 10, "lt": 100, "multiple_of": 10}),
    ],
)
def test_create_numerical_constrained_field_schema_pydantic_v2(
    make_constraint: Any,
    constraint_kwargs: dict[str, Any],
    schema_creator: SchemaCreator,
    plugin: PydanticSchemaPlugin,
) -> None:
    annotation = make_constraint(**constraint_kwargs)

    class Model(pydantic_v2.BaseModel):
        field: annotation  # type: ignore[valid-type]

    schema = schema_creator.for_plugin(FieldDefinition.from_annotation(Model), plugin).properties["field"]  # pyright: ignore[reportAttributeAccessIssue]

    assert schema.type == OpenAPIType.INTEGER if is_class_and_subclass(annotation, int) else OpenAPIType.NUMBER  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.exclusive_minimum == constraint_kwargs.get("gt")  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.minimum == constraint_kwargs.get("ge")  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.exclusive_maximum == constraint_kwargs.get("lt")  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.maximum == constraint_kwargs.get("le")  # pyright: ignore[reportAttributeAccessIssue]
    assert schema.multiple_of == constraint_kwargs.get("multiple_of")  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    ("constraints", "description"),
    [
        ({"gt": date(2020, 1, 1), "lt": date(2030, 1, 1)}, "must be after 2020-01-01 and before 2030-01-01"),
        (
            {"ge": date(2020, 1, 1), "le": date(2030, 1, 1)},
            "must be on or after 2020-01-01 and on or before 2030-01-01",
        ),
    ],
)
def test_create_date_constrained_field_schema_pydantic_v2(
    constraints: dict[str, Any],
    description: str,
    schema_creator: SchemaCreator,
    plugin: PydanticSchemaPlugin,
) -> None:
    class Model(pydantic_v2.BaseModel):
        field: pydantic_v2.condate(**constraints)  # type: ignore[valid-type]

    schema = schema_creator.for_plugin(FieldDefinition.from_annotation(Model), plugin).properties["field"]

    assert schema.to_schema() == {"type": "string", "format": "date", "description": description}


@pytest.mark.parametrize(
    "annotation",
    [
        *constrained_numbers_v2,
        *constrained_collection_v2,
        *constrained_string_v2,
        *constrained_dates_v2,
    ],
)
def test_create_constrained_field_schema_v2(
    annotation: Any,
    schema_creator: SchemaCreator,
    plugin: PydanticSchemaPlugin,
) -> None:
    class Model(pydantic_v2.BaseModel):
        field: annotation

    assert schema_creator.for_plugin(FieldDefinition.from_annotation(Model), plugin).properties["field"]


@pytest.mark.parametrize("cls", (PydanticPerson, PydanticDataclassPerson))
def test_spec_generation(cls: Any) -> None:
    @post("/")
    def handler(data: JSONBody[cls]) -> cls:
        return data

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema

        assert schema.to_schema()["components"]["schemas"][cls.__name__] == {
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "id": {"type": "string"},
                "optional": {"type": ["string", "null"]},
                "complex": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                },
                "union": {"oneOf": [{"type": "integer"}, {"items": {"type": "string"}, "type": "array"}]},
                "pets": {
                    "oneOf": [
                        {
                            "items": {"$ref": "#/components/schemas/DataclassPet"},
                            "type": "array",
                        },
                        {"type": "null"},
                    ]
                },
            },
            "type": "object",
            "required": ["complex", "first_name", "id", "last_name", "optional", "union"],
            "title": f"{cls.__name__}",
        }


def test_schema_generation_v2() -> None:
    class Lookup(pydantic_v2.BaseModel):
        id: Annotated[
            str,
            pydantic_v2.Field(
                min_length=12,
                max_length=16,
                description="A unique identifier",
                # we expect these examples to be merged
                json_schema_extra={"example": "e4eaaaf2-d142-11e1-b3e4-080027620cdd", "examples": ["31"]},
                examples=["32"],
            ),
        ]
        # title should work if given on the field
        with_title: str = pydantic_v2.Field(title="WITH_title")
        # or as an extra
        with_extra_title: str = pydantic_v2.Field(json_schema_extra={"title": "WITH_extra"})
        # moreover, we allow json_schema_extra to use names that exactly match the JSONSchema spec
        without_duplicates: list[str] = pydantic_v2.Field(json_schema_extra={"uniqueItems": True})

    @post("/example")
    async def example_route() -> Lookup:
        return Lookup(id="1234567812345678", with_title="1", with_extra_title="2", without_duplicates=[])

    app = Litestar([example_route])
    schema = app.openapi_schema.to_schema()
    lookup_schema = schema["components"]["schemas"]["test_schema_generation_v2.Lookup"]["properties"]

    assert lookup_schema["id"] == {
        "description": "A unique identifier",
        "examples": ["e4eaaaf2-d142-11e1-b3e4-080027620cdd", "31", "32"],
        "maxLength": 16,
        "minLength": 12,
        "type": "string",
    }
    assert lookup_schema["with_title"] == {"title": "WITH_title", "type": "string"}
    assert lookup_schema["with_extra_title"] == {"title": "WITH_extra", "type": "string"}
    assert lookup_schema["without_duplicates"] == {"type": "array", "items": {"type": "string"}, "uniqueItems": True}


def test_create_examples(pydantic_version: PydanticVersion) -> None:
    class Model(pydantic_v2.BaseModel):
        foo: str = pydantic_v2.Field(examples=["32"])
        bar: str

    @get("/example")
    async def handler() -> Model:
        return Model(foo="1", bar="2")

    app = Litestar(
        [handler],
        openapi_config=OpenAPIConfig(
            title="Test",
            version="0",
            create_examples=True,
        ),
    )
    schema = app.openapi_schema.to_schema()
    lookup_schema = schema["components"]["schemas"]["test_create_examples.Model"]["properties"]

    assert lookup_schema["foo"]["examples"] == ["32"]
    assert lookup_schema["bar"]["examples"]


def test_v2_json_schema_extra_callable_raises() -> None:
    class Model(pydantic_v2.BaseModel):
        field: str = pydantic_v2.Field(json_schema_extra=lambda e: None)

    @get("/example")
    def handler() -> Model:
        return Model(field="1")

    app = Litestar([handler])
    with pytest.raises(ValueError, match="Callables not supported"):
        app.openapi_schema


def test_schema_by_alias(base_model: AnyBaseModelType, pydantic_version: PydanticVersion) -> None:
    class RequestWithAlias(base_model):  # type: ignore[valid-type,misc]
        first: str = pydantic_v2.Field(alias="second")

    class ResponseWithAlias(base_model):  # type: ignore[valid-type,misc]
        first: str = pydantic_v2.Field(alias="second")

    @post("/", signature_types=[RequestWithAlias, ResponseWithAlias])
    def handler(data: JSONBody[RequestWithAlias]) -> ResponseWithAlias:
        return ResponseWithAlias(second=data.first)

    app = Litestar(route_handlers=[handler], openapi_config=OpenAPIConfig(title="my title", version="1.0.0"))

    assert app.openapi_schema
    schemas = app.openapi_schema.to_schema()["components"]["schemas"]
    request_key = "second"
    assert schemas["test_schema_by_alias.RequestWithAlias"] == {
        "properties": {request_key: {"type": "string"}},
        "type": "object",
        "required": [request_key],
        "title": "RequestWithAlias",
    }
    response_key = "first"
    assert schemas["test_schema_by_alias.ResponseWithAlias"] == {
        "properties": {response_key: {"type": "string"}},
        "type": "object",
        "required": [response_key],
        "title": "ResponseWithAlias",
    }

    with TestClient(app) as client:
        response = client.post("/", json={request_key: "foo"})
        assert response.json() == {response_key: "foo"}


def test_schema_by_alias_plugin_override(base_model: AnyBaseModelType, pydantic_version: PydanticVersion) -> None:
    class RequestWithAlias(base_model):  # type: ignore[misc, valid-type]
        first: str = pydantic_v2.Field(alias="second")

    class ResponseWithAlias(base_model):  # type: ignore[misc, valid-type]
        first: str = pydantic_v2.Field(alias="second")

    @post("/", signature_types=[RequestWithAlias, ResponseWithAlias])
    def handler(data: JSONBody[RequestWithAlias]) -> ResponseWithAlias:
        return ResponseWithAlias(second=data.first)

    app = Litestar(
        route_handlers=[handler],
        openapi_config=OpenAPIConfig(title="my title", version="1.0.0"),
        plugins=[PydanticPlugin(prefer_alias=True)],
    )
    assert app.openapi_schema
    schemas = app.openapi_schema.to_schema()["components"]["schemas"]
    request_key = "second"
    assert schemas["test_schema_by_alias_plugin_override.RequestWithAlias"] == {
        "properties": {request_key: {"type": "string"}},
        "type": "object",
        "required": [request_key],
        "title": "RequestWithAlias",
    }
    response_key = "second"
    assert schemas["test_schema_by_alias_plugin_override.ResponseWithAlias"] == {
        "properties": {response_key: {"type": "string"}},
        "type": "object",
        "required": [response_key],
        "title": "ResponseWithAlias",
    }

    with TestClient(app) as client:
        response = client.post("/", json={request_key: "foo"})
        assert response.json() == {response_key: "foo"}


def test_create_schema_for_field_v2() -> None:
    class Model(pydantic_v2.BaseModel):
        value: str = pydantic_v2.Field(
            title="title", description="description", max_length=16, json_schema_extra={"example": "example"}
        )

    schema = get_schema_for_field_definition(
        FieldDefinition.from_kwarg(name="Model", annotation=Model), plugins=[PydanticSchemaPlugin()]
    )

    assert schema.properties

    value = schema.properties["value"]

    assert isinstance(value, Schema)
    assert value.description == "description"
    assert value.title == "title"
    assert value.examples == ["example"]


def test_create_schema_for_field_v2_examples() -> None:
    class Model(pydantic_v2.BaseModel):
        value: str = pydantic_v2.Field(
            title="title", description="description", max_length=16, json_schema_extra={"examples": ["example"]}
        )

    schema = get_schema_for_field_definition(
        FieldDefinition.from_kwarg(name="Model", annotation=Model), plugins=[PydanticSchemaPlugin()]
    )

    assert schema.properties

    value = schema.properties["value"]

    assert isinstance(value, Schema)
    assert value.description == "description"
    assert value.title == "title"
    assert value.examples == ["example"]


@pytest.mark.parametrize("with_future_annotations", [True, False])
def test_create_schema_for_pydantic_model_with_annotated_model_attribute(
    with_future_annotations: bool, create_module: "Callable[[str], ModuleType]", pydantic_version: PydanticVersion
) -> None:
    """Test that a model with an annotated attribute is correctly handled."""
    module = create_module(
        f"""
{"from __future__ import annotations" if with_future_annotations else ""}
from typing_extensions import Annotated
from pydantic import BaseModel

class Foo(BaseModel):
    foo: Annotated[int, "Foo description"]
"""
    )
    creator = SchemaCreator(plugins=[PydanticSchemaPlugin()])
    creator.for_field_definition(FieldDefinition.from_annotation(module.Foo))
    schemas = creator.schema_registry.generate_components_schemas()
    schema = schemas["Foo"]
    assert schema.properties and "foo" in schema.properties


def test_create_schema_for_pydantic_model_with_unhashable_literal_default(
    create_module: "Callable[[str], ModuleType]",
) -> None:
    """Test that a model with unhashable literal defaults is correctly handled."""
    module = create_module(
        """
from pydantic import BaseModel, Field

class Model(BaseModel):
    id: int
    dict_default: dict = {}
    dict_default_in_field: dict = Field(default={})
    dict_default_in_factory: dict = Field(default_factory=dict)
    list_default: list = []
    list_default_in_field: list = Field(default=[])
    list_default_in_factory: list = Field(default_factory=list)
"""
    )
    creator = SchemaCreator(plugins=[PydanticSchemaPlugin()])
    creator.for_field_definition(FieldDefinition.from_annotation(module.Model))
    schemas = creator.schema_registry.generate_components_schemas()
    schema = schemas["Model"]
    assert schema.properties
    assert "dict_default" in schema.properties
    assert "dict_default_in_field" in schema.properties
    assert "dict_default_in_factory" in schema.properties
    assert "list_default" in schema.properties
    assert "list_default_in_field" in schema.properties
    assert "list_default_in_factory" in schema.properties


@pytest.mark.parametrize("field_type", [pydantic_v2.AnyUrl, pydantic_v2.AnyHttpUrl, pydantic_v2.HttpUrl])
def test_create_for_url_v2(field_type: Any) -> None:
    field_definition = FieldDefinition.from_annotation(field_type)
    schema = SchemaCreator(plugins=[PydanticSchemaPlugin()]).for_field_definition(field_definition)
    assert schema.type == OpenAPIType.STRING
    assert schema.format == OpenAPIFormat.URL


@pytest.mark.parametrize("prefer_alias", [True, False])
def test_create_for_computed_field(prefer_alias: bool) -> None:
    class Sample(pydantic_v2.BaseModel):
        property_one: str

        @pydantic_v2.computed_field(
            description="a description", title="a title", alias="prop_two" if prefer_alias else None
        )
        def property_two(self) -> bool:
            return True

    field_definition = FieldDefinition.from_annotation(Sample)
    schema_creator = SchemaCreator(plugins=[PydanticSchemaPlugin()])
    ref = schema_creator.for_field_definition(field_definition)
    assert isinstance(ref, Reference)
    registered_schemas = list(schema_creator.schema_registry)
    assert len(registered_schemas) == 1
    schema = registered_schemas[0].schema
    assert schema.required == ["property_one", "property_two"] if not prefer_alias else ["property_one", "prop_two"]
    properties = schema.properties
    assert properties is not None
    assert properties.keys() == {"property_one", "property_two"} if not prefer_alias else {"property_one", "prop_two"}
    property_two = properties["property_two"] if not prefer_alias else properties["prop_two"]
    assert isinstance(property_two, Schema)
    assert property_two.type == OpenAPIType.BOOLEAN
    assert property_two.description == "a description"
    assert property_two.title == "a title"
    assert property_two.read_only


PATTERN = "^[a-z]+$"
UNICODE_PATTERN = r"^\p{L}+$"


class PatternModel(pydantic_v2.BaseModel):
    field: str = pydantic_v2.Field(pattern=PATTERN)
    field_with_length: str = pydantic_v2.Field(min_length=2, max_length=5, pattern=PATTERN)
    annotated_field: Annotated[str, pydantic_v2.Field(pattern=PATTERN)]
    compiled: str = pydantic_v2.Field(pattern=re.compile(PATTERN))
    constr_type: pydantic_v2.constr(pattern=PATTERN)  # type: ignore[valid-type]
    string_constraints: Annotated[str, pydantic_v2.StringConstraints(pattern=PATTERN)]
    compiled_string_constraints: Annotated[str, pydantic_v2.StringConstraints(pattern=re.compile(PATTERN))]
    optional_field: Optional[str] = pydantic_v2.Field(None, pattern=PATTERN)
    optional_compiled: Optional[str] = pydantic_v2.Field(None, pattern=re.compile(PATTERN))
    optional_constr: Optional[pydantic_v2.constr(pattern=PATTERN)] = None  # type: ignore[valid-type]
    optional_compiled_string_constraints: Annotated[
        Optional[str], pydantic_v2.StringConstraints(pattern=re.compile(PATTERN))
    ] = None
    list_of_constr: list[pydantic_v2.constr(pattern=PATTERN)] = []  # type: ignore[valid-type]
    list_of_field: list[Annotated[str, pydantic_v2.Field(pattern=PATTERN)]] = []
    dict_of_constr: dict[str, pydantic_v2.constr(pattern=PATTERN)] = {}  # type: ignore[valid-type]
    union_constr: Union[int, pydantic_v2.constr(pattern=PATTERN)] = 1  # type: ignore[valid-type]
    factory_list: list[pydantic_v2.constr(pattern=PATTERN)] = pydantic_v2.Field(  # type: ignore[valid-type]
        default_factory=list
    )
    described: str = pydantic_v2.Field("abc", pattern=PATTERN, description="lower case letters")
    tuple_of_constr: tuple[pydantic_v2.constr(pattern=PATTERN), ...] = ()  # type: ignore[valid-type]
    fixed_tuple: tuple[int, pydantic_v2.constr(pattern=PATTERN)] = (1, "a")  # type: ignore[valid-type]
    set_of_constr: set[pydantic_v2.constr(pattern=PATTERN)] = pydantic_v2.Field(  # type: ignore[valid-type]
        default_factory=set
    )
    sequence_of_constr: Sequence[pydantic_v2.constr(pattern=PATTERN)] = ()  # type: ignore[valid-type]
    mapping_of_constr: Mapping[str, pydantic_v2.constr(pattern=PATTERN)] = {}  # type: ignore[valid-type]
    case_insensitive: str = pydantic_v2.Field("a", pattern=re.compile(PATTERN, re.IGNORECASE))
    case_insensitive_constr: pydantic_v2.constr(  # type: ignore[valid-type]
        pattern=re.compile(PATTERN, re.IGNORECASE)
    ) = "a"


PATTERN_STRING = {"type": "string", "pattern": PATTERN}
PATTERN_SCHEMAS: dict[str, dict[str, Any]] = {
    "field": PATTERN_STRING,
    "field_with_length": {"type": "string", "minLength": 2, "maxLength": 5, "pattern": PATTERN},
    "annotated_field": PATTERN_STRING,
    "compiled": PATTERN_STRING,
    "constr_type": PATTERN_STRING,
    "string_constraints": PATTERN_STRING,
    "compiled_string_constraints": PATTERN_STRING,
    "optional_field": {"type": ["string", "null"], "pattern": PATTERN},
    "optional_compiled": {"type": ["string", "null"], "pattern": PATTERN},
    "optional_constr": {"type": ["string", "null"], "pattern": PATTERN},
    "optional_compiled_string_constraints": {"type": ["string", "null"], "pattern": PATTERN},
    "list_of_constr": {"type": "array", "items": PATTERN_STRING, "default": []},
    "list_of_field": {"type": "array", "items": PATTERN_STRING, "default": []},
    "dict_of_constr": {"type": "object", "additionalProperties": PATTERN_STRING, "default": {}},
    "union_constr": {"oneOf": [{"type": "integer"}, PATTERN_STRING], "default": 1},
    "factory_list": {"type": "array", "items": PATTERN_STRING},
    "described": {"type": "string", "pattern": PATTERN, "description": "lower case letters", "default": "abc"},
    "tuple_of_constr": {"type": "array", "items": PATTERN_STRING, "default": ()},
    "fixed_tuple": {
        "type": "array",
        "prefixItems": [{"type": "integer"}, PATTERN_STRING],
        "minItems": 2,
        "maxItems": 2,
        "default": (1, "a"),
    },
    "set_of_constr": {"type": "array", "items": PATTERN_STRING},
    "sequence_of_constr": {"type": "array", "items": PATTERN_STRING, "default": ()},
    "mapping_of_constr": {"type": "object", "additionalProperties": PATTERN_STRING, "default": {}},
    "case_insensitive": {"type": "string", "default": "a"},
    "case_insensitive_constr": {"type": "string", "default": "a"},
}


@post("/pattern", sync_to_thread=False)
def pattern_handler(data: JSONBody[PatternModel]) -> None:
    return None


def test_pattern_is_documented() -> None:
    schema = Litestar([pattern_handler]).openapi_schema.to_schema()
    assert schema["components"]["schemas"]["PatternModel"]["properties"] == PATTERN_SCHEMAS


class UnicodePatternModel(pydantic_v2.BaseModel):
    value: str = pydantic_v2.Field("a", pattern=UNICODE_PATTERN)


def test_unicode_property_pattern_is_documented_verbatim(validate_generated_openapi_documents: list[str]) -> None:
    @post("/unicode", sync_to_thread=False)
    def handler(data: JSONBody[UnicodePatternModel]) -> None:
        return None

    schema = Litestar([handler]).openapi_schema.to_schema()

    assert schema["components"]["schemas"]["UnicodePatternModel"]["properties"]["value"] == {
        "type": "string",
        "pattern": UNICODE_PATTERN,
        "default": "a",
    }
    errors = list(validate_generated_openapi_documents)
    validate_generated_openapi_documents.clear()
    assert errors == [f"{UNICODE_PATTERN!r} is not a 'regex'"]


def test_handler_parameter_pattern_is_not_enforced() -> None:
    def provide_value(
        dependency_value: FromQuery[pydantic_v2.constr(min_length=2, pattern=PATTERN)],  # type: ignore[valid-type]
    ) -> str:
        return dependency_value  # type: ignore[no-any-return]

    @get("/unicode", sync_to_thread=False)
    def unicode_handler(
        value: FromQuery[pydantic_v2.constr(pattern=UNICODE_PATTERN)],  # type: ignore[valid-type]
    ) -> str:
        return value  # type: ignore[no-any-return]

    @get("/dependency", dependencies={"provided": Provide(provide_value, sync_to_thread=False)}, sync_to_thread=False)
    def dependency_handler(provided: NamedDependency[str]) -> str:
        return provided

    @get("/union", sync_to_thread=False)
    def union_handler(
        value: FromQuery[Annotated[Union[str, int], pydantic_v2.StringConstraints(pattern=PATTERN)]],
    ) -> str:
        return str(value)

    with create_test_client([unicode_handler, dependency_handler, union_handler]) as client:
        paths = client.app.openapi_schema.to_schema()["paths"]
        assert paths["/unicode"]["get"]["parameters"][0]["schema"] == {"type": "string"}
        assert paths["/dependency"]["get"]["parameters"][0]["schema"] == {"type": "string", "minLength": 2}
        assert paths["/union"]["get"]["parameters"][0]["schema"] == {"oneOf": [{"type": "string"}, {"type": "integer"}]}

        assert client.get("/unicode", params={"value": "abc"}).status_code == 200
        assert client.get("/dependency", params={"dependency_value": "AB1"}).status_code == 200
        assert client.get("/dependency", params={"dependency_value": "a"}).status_code == 400
        assert client.get("/union", params={"value": "abc"}).status_code == 200
        assert client.get("/union", params={"value": "1"}).status_code == 200


DECIMAL_SCHEMA = {
    "oneOf": [
        {"type": "number"},
        {"type": "string", "pattern": r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$"},
    ]
}


@pytest.mark.parametrize(
    ("constraint_kwargs", "bounds"),
    [
        ({"gt": Decimal("10"), "lt": Decimal("100")}, {"exclusiveMinimum": 10.0, "exclusiveMaximum": 100.0}),
        ({"ge": Decimal("10"), "le": Decimal("100")}, {"minimum": 10.0, "maximum": 100.0}),
        ({"gt": Decimal("10"), "multiple_of": Decimal("5")}, {"exclusiveMinimum": 10.0, "multipleOf": 5.0}),
    ],
)
def test_create_decimal_constrained_field_schema_pydantic_v2(
    constraint_kwargs: dict[str, Any],
    bounds: dict[str, float],
    schema_creator: SchemaCreator,
    plugin: PydanticSchemaPlugin,
) -> None:
    class Model(pydantic_v2.BaseModel):
        field: pydantic_v2.condecimal(**constraint_kwargs)  # type: ignore[valid-type]

    schema = schema_creator.for_plugin(FieldDefinition.from_annotation(Model), plugin).properties["field"]

    assert schema.to_schema() == {**DECIMAL_SCHEMA, **bounds}


def test_constrained_decimal_and_date_fields_document_what_the_server_enforces() -> None:
    class Model(pydantic_v2.BaseModel):
        price: Decimal = pydantic_v2.Field(gt=0)
        day: date = pydantic_v2.Field(ge=date(2020, 1, 1))
        maybe_day: Optional[date] = pydantic_v2.Field(default=None, ge=date(2020, 1, 1))

    @post("/", sync_to_thread=False)
    def handler(data: JSONBody[Model]) -> Model:
        return data

    with create_test_client(handler) as client:
        (component,) = client.app.openapi_schema.to_schema()["components"]["schemas"].values()
        assert component["properties"] == {
            "price": {**DECIMAL_SCHEMA, "exclusiveMinimum": 0},
            "day": {"type": "string", "format": "date", "description": "must be on or after 2020-01-01"},
            "maybe_day": {
                "type": ["string", "null"],
                "format": "date",
                "description": "must be on or after 2020-01-01",
            },
        }

        for price in ("1.5", 1.5, "1E+3"):
            response = client.post("/", json={"price": price, "day": "2021-01-01"})
            assert response.status_code == 201
            assert isinstance(response.json()["price"], str)
        assert client.post("/", json={"price": 0, "day": "2021-01-01"}).status_code == 400
        assert client.post("/", json={"price": "abc", "day": "2021-01-01"}).status_code == 400
        assert client.post("/", json={"price": "1.5", "day": "2019-12-31"}).status_code == 400


def test_constrained_collection_fields_match_the_server() -> None:
    class Model(pydantic_v2.BaseModel):
        mapping: dict[str, int] = pydantic_v2.Field(min_length=1, max_length=2)
        optional_mapping: Optional[dict[str, int]] = pydantic_v2.Field(default=None, min_length=1)
        optional_sequence: Optional[list[int]] = pydantic_v2.Field(default=None, min_length=2)

    @post("/", sync_to_thread=False)
    def handler(data: JSONBody[Model]) -> None:
        return None

    with create_test_client(handler) as client:
        (component,) = client.app.openapi_schema.to_schema()["components"]["schemas"].values()
        assert component["properties"] == {
            "mapping": {
                "type": "object",
                "additionalProperties": {"type": "integer"},
                "minProperties": 1,
                "maxProperties": 2,
            },
            "optional_mapping": {
                "oneOf": [{"type": "object", "additionalProperties": {"type": "integer"}}, {"type": "null"}],
                "minProperties": 1,
            },
            "optional_sequence": {
                "oneOf": [{"type": "array", "items": {"type": "integer"}}, {"type": "null"}],
                "minItems": 2,
            },
        }

        assert client.post("/", json={"mapping": {"a": 1}}).status_code == 201
        assert client.post("/", json={"mapping": {}}).status_code == 400
        assert client.post("/", json={"mapping": {"a": 1, "b": 2, "c": 3}}).status_code == 400
        assert client.post("/", json={"mapping": {"a": 1}, "optional_mapping": {}}).status_code == 400
        assert client.post("/", json={"mapping": {"a": 1}, "optional_sequence": [1]}).status_code == 400


@pytest.mark.skipif(sys.version_info < (3, 12), reason="type statement not available before 3.12")
def test_type_alias_field_constraints() -> None:
    namespace: dict[str, Any] = {"__name__": __name__, "Annotated": Annotated, "Field": pydantic_v2.Field}
    exec(
        "type Limit = Annotated[int, Field(ge=0)]\n"
        "type Outer = Limit\n"
        "type Bounded[T] = Annotated[T, Field(ge=0)]\n"
        "type Name = Annotated[str, Field(max_length=5)]\n"
        "type Items[T] = Annotated[list[T], Field(min_length=1)]\n"
        "type Code = Annotated[str, Field(min_length=2, max_length=5, pattern='^a')]",
        namespace,
    )
    limit, name = namespace["Limit"], namespace["Name"]
    model = pydantic_v2.create_model(
        "Model",
        extended=(Annotated[limit, pydantic_v2.Field(le=10)], ...),
        overridden=(Annotated[limit, pydantic_v2.Field(ge=5)], ...),
        nested=(namespace["Outer"], ...),
        generic=(namespace["Bounded"][int], ...),
        name=(name, ...),
        shortened=(Annotated[name, pydantic_v2.StringConstraints(max_length=3)], ...),
        items=(namespace["Items"][int], ...),
        code=(namespace["Code"], ...),
    )

    @post("/")
    async def handler(data: JSONBody[model]) -> None:  # type: ignore[valid-type]
        return None

    payload = {
        "extended": 1,
        "overridden": 6,
        "nested": 1,
        "generic": 1,
        "name": "abc",
        "shortened": "abc",
        "items": [1],
        "code": "abc",
    }
    with create_test_client([handler]) as client:
        properties = client.app.openapi_schema.to_schema()["components"]["schemas"]["Model"]["properties"]
        assert (properties["extended"]["minimum"], properties["extended"]["maximum"]) == (0, 10)
        assert properties["overridden"]["minimum"] == 5
        assert properties["nested"]["minimum"] == 0
        assert properties["generic"]["minimum"] == 0
        assert properties["name"]["maxLength"] == 5
        assert properties["shortened"]["maxLength"] == 3
        assert properties["items"]["minItems"] == 1
        assert properties["code"] == {"type": "string", "minLength": 2, "maxLength": 5, "pattern": "^a"}
        assert client.post("/", json=payload).status_code == 201
        assert client.post("/", json={**payload, "nested": -1}).status_code == 400
        assert client.post("/", json={**payload, "shortened": "abcd"}).status_code == 400
        assert client.post("/", json={**payload, "items": []}).status_code == 400
        assert client.post("/", json={**payload, "code": "zz"}).status_code == 400


ExampleT = TypeVar("ExampleT")


class ExampleBase(pydantic_v2.BaseModel):
    value: int = pydantic_v2.Field(json_schema_extra={"example": 5})


class ExampleChild(ExampleBase):
    other: int = 0


class ExampleGeneric(pydantic_v2.BaseModel, Generic[ExampleT]):
    value: int = pydantic_v2.Field(json_schema_extra={"example": 5})
    item: ExampleT


class ExampleDTOModel(pydantic_v2.BaseModel):
    value: int = pydantic_v2.Field(json_schema_extra={"example": 5})


@pytest.mark.parametrize(
    "field_kwargs, expected",
    [
        ({"json_schema_extra": {"example": 5}}, {"type": "integer", "examples": [5]}),
        ({"json_schema_extra": {"examples": [5, 6]}}, {"type": "integer", "examples": [5, 6]}),
        ({"json_schema_extra": {"example": 5, "examples": [6]}}, {"type": "integer", "examples": [5, 6]}),
        (
            {"json_schema_extra": {"example": 5, "deprecated": True}},
            {"type": "integer", "deprecated": True, "examples": [5]},
        ),
        (
            {"examples": [7], "json_schema_extra": {"deprecated": True}},
            {"type": "integer", "deprecated": True, "examples": [7]},
        ),
        ({"examples": [7], "json_schema_extra": {"example": 5}}, {"type": "integer", "examples": [5, 7]}),
    ],
    ids=["example", "examples", "both", "other-keys", "field-examples", "field-examples-and-example"],
)
def test_schema_generation_does_not_mutate_json_schema_extra(
    field_kwargs: dict[str, Any], expected: dict[str, Any]
) -> None:
    class Model(pydantic_v2.BaseModel):
        value: int = pydantic_v2.Field(**copy.deepcopy(field_kwargs))

    @get("/", sync_to_thread=False)
    def handler() -> Model:
        return Model(value=1)

    json_schema_extra = Model.model_fields["value"].json_schema_extra
    before = copy.deepcopy(json_schema_extra)

    first = Litestar([handler]).openapi_schema.to_schema()
    second = Litestar([handler]).openapi_schema.to_schema()

    (component,) = first["components"]["schemas"].values()
    assert component["properties"]["value"] == expected
    assert second == first
    assert Model.model_fields["value"].json_schema_extra is json_schema_extra
    assert json_schema_extra == before


def test_json_schema_extra_examples_are_documented_for_every_usage() -> None:
    @get("/base", sync_to_thread=False)
    def base() -> ExampleBase:
        return ExampleBase(value=1)

    @get("/child", sync_to_thread=False)
    def child() -> ExampleChild:
        return ExampleChild(value=1)

    @get("/int", sync_to_thread=False)
    def generic_int() -> ExampleGeneric[int]:
        return ExampleGeneric[int](value=1, item=1)

    @get("/str", sync_to_thread=False)
    def generic_str() -> ExampleGeneric[str]:
        return ExampleGeneric[str](value=1, item="a")

    @get("/dto", return_dto=PydanticDTO[ExampleDTOModel], sync_to_thread=False)
    def dto() -> ExampleDTOModel:
        return ExampleDTOModel(value=1)

    @post("/plain", sync_to_thread=False)
    def plain(data: JSONBody[ExampleDTOModel]) -> None:
        return None

    schema = Litestar([base, child, generic_int, generic_str, dto, plain]).openapi_schema.to_schema()
    values = {name: component["properties"]["value"] for name, component in schema["components"]["schemas"].items()}

    assert len(values) == 6
    assert all(value == {"type": "integer", "examples": [5]} for value in values.values()), values
    assert ExampleBase.model_fields["value"].json_schema_extra == {"example": 5}
    assert ExampleGeneric.model_fields["value"].json_schema_extra == {"example": 5}
    assert ExampleDTOModel.model_fields["value"].json_schema_extra == {"example": 5}


def test_json_schema_extra_extension_keys() -> None:
    class Inner(pydantic_v2.BaseModel):
        a: int

    class Model(pydantic_v2.BaseModel):
        inline: int = pydantic_v2.Field(json_schema_extra={"x-internal": True})
        reference: Inner = pydantic_v2.Field(json_schema_extra={"x-owner": {"team": "a"}})
        mixed: str = pydantic_v2.Field("d", json_schema_extra={"x-a": 1, "format": "foo", "example": "e"})

    @get("/", sync_to_thread=False)
    def handler() -> Model:
        return Model(inline=1, reference=Inner(a=1))

    schemas = Litestar([handler]).openapi_schema.to_schema()["components"]["schemas"]
    inner_name = "test_json_schema_extra_extension_keys.Inner"

    assert schemas["test_json_schema_extra_extension_keys.Model"]["properties"] == {
        "inline": {"type": "integer", "x-internal": True},
        "reference": {"allOf": [{"$ref": f"#/components/schemas/{inner_name}"}], "x-owner": {"team": "a"}},
        "mixed": {"type": "string", "format": "foo", "default": "d", "examples": ["e"], "x-a": 1},
    }
    assert schemas[inner_name] == {
        "properties": {"a": {"type": "integer"}},
        "type": "object",
        "required": ["a"],
        "title": "Inner",
    }
    assert Model.model_fields["inline"].json_schema_extra == {"x-internal": True}


def test_extra_forbid_documents_additional_properties() -> None:
    class Forbid(pydantic_v2.BaseModel):
        model_config = pydantic_v2.ConfigDict(extra="forbid")
        value: int

        @pydantic_v2.computed_field  # type: ignore[prop-decorator]
        @property
        def double(self) -> int:
            return self.value * 2

    class ForbidChild(Forbid):
        other: int = 0

    class AllowChild(Forbid):
        model_config = pydantic_v2.ConfigDict(extra="allow")

    class Ignore(pydantic_v2.BaseModel):
        value: int

    class GenericForbid(pydantic_v2.BaseModel, Generic[T]):
        model_config = pydantic_v2.ConfigDict(extra="forbid")
        value: T

    @post("/forbid")
    async def forbid(data: JSONBody[Forbid]) -> Forbid:
        return data

    @post("/forbid-child")
    async def forbid_child(data: JSONBody[ForbidChild]) -> ForbidChild:
        return data

    @post("/generic-forbid")
    async def generic_forbid(data: JSONBody[GenericForbid[int]]) -> GenericForbid[int]:
        return data

    @post("/allow-child")
    async def allow_child(data: JSONBody[AllowChild]) -> AllowChild:
        return data

    @post("/ignore")
    async def ignore(data: JSONBody[Ignore]) -> Ignore:
        return data

    handlers = [forbid, forbid_child, generic_forbid, allow_child, ignore]

    with create_test_client(handlers) as client:
        document = client.app.openapi_schema.to_schema()

        assert request_body_component(document, "/forbid")["additionalProperties"] is False

        for path in ("/forbid-child", "/generic-forbid"):
            component = request_body_component(document, path)
            assert component["additionalProperties"] is False
            assert client.post(path, json={"value": 1, "unknown": 1}).status_code == 400
            assert client.post(path, json={"value": 1}).json().keys() <= component["properties"].keys()

        for path in ("/allow-child", "/ignore"):
            assert "additionalProperties" not in request_body_component(document, path)
            assert client.post(path, json={"value": 1, "unknown": 1}).status_code == 201


def test_extra_forbid_with_field_aliases_documents_no_additional_properties() -> None:
    class Validation(pydantic_v2.BaseModel):
        model_config = pydantic_v2.ConfigDict(extra="forbid")
        value: int = pydantic_v2.Field(default=1, validation_alias="wireValue")

    generated_model: Any = pydantic_v2.create_model(
        "Generated",
        __config__=pydantic_v2.ConfigDict(extra="forbid", alias_generator=to_camel),
        user_name=(str, "x"),
    )

    class PopulateByName(pydantic_v2.BaseModel):
        model_config = pydantic_v2.ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)
        user_name: str = "x"

    class ValidateByName(pydantic_v2.BaseModel):
        model_config = pydantic_v2.ConfigDict(extra="forbid", alias_generator=to_camel, validate_by_name=True)
        user_name: str = "x"

    @post("/validation")
    async def validation(data: JSONBody[Validation]) -> Validation:
        return data

    @post("/generated")
    async def generated(data: JSONBody[generated_model]) -> None:
        return None

    @post("/populate-by-name")
    async def populate_by_name(data: JSONBody[PopulateByName]) -> None:
        return None

    @post("/validate-by-name")
    async def validate_by_name(data: JSONBody[ValidateByName]) -> None:
        return None

    with create_test_client([validation, generated, populate_by_name, validate_by_name]) as client:
        document = client.app.openapi_schema.to_schema()

        for path in ("/validation", "/generated", "/populate-by-name", "/validate-by-name"):
            assert "additionalProperties" not in request_body_component(document, path)
        assert client.post("/validation", json={"wireValue": 2}).json() == {"value": 2}
        for path in ("/populate-by-name", "/validate-by-name"):
            assert client.post(path, json={"userName": "a"}).status_code == 201
            assert client.post(path, json={"user_name": "a"}).status_code == 201


def test_ip_any_interface_and_network_document_no_format() -> None:
    class Model(pydantic_v2.BaseModel):
        address: pydantic_v2.IPvAnyAddress
        interface: pydantic_v2.IPvAnyInterface
        network: pydantic_v2.IPvAnyNetwork

    @post("/")
    async def handler(data: JSONBody[Model]) -> Model:
        return data

    payload = {"address": "192.168.0.1", "interface": "2001:db8::1/64", "network": "192.168.0.0/24"}

    with create_test_client([handler]) as client:
        (component,) = client.app.openapi_schema.to_schema()["components"]["schemas"].values()
        assert client.post("/", json=payload).json() == payload

    assert component["properties"]["interface"] == {"type": "string"}
    assert component["properties"]["network"] == {"type": "string"}
    assert component["properties"]["address"] == {
        "anyOf": [
            {"type": "string", "format": "ipv4", "description": "IPv4 address"},
            {"type": "string", "format": "ipv6", "description": "IPv6 address"},
        ]
    }
