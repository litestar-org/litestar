from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Interface, IPv6Network
from types import ModuleType
from typing import Annotated, Any, Optional, Union

import annotated_types
import pydantic as pydantic_v2
import pytest
from pydantic_core import core_schema
from typing_extensions import TypeAliasType

from litestar import Litestar, get, post
from litestar._openapi.schema_generation.schema import SchemaCreator
from litestar.openapi import OpenAPIConfig
from litestar.openapi.spec import Schema
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.params import FromQuery, JSONBody
from litestar.plugins.pydantic import PydanticDTO, PydanticPlugin, PydanticSchemaPlugin
from litestar.plugins.pydantic.plugins.schema import _RegisteredFormatsJsonSchema
from litestar.testing import TestClient, create_test_client
from litestar.typing import FieldDefinition
from litestar.utils import is_class_and_subclass
from tests.unit.test_plugins.test_pydantic.models import (
    PydanticDataclassPerson,
    PydanticPerson,
)

from . import PydanticVersion, pydantic_document

AnyBaseModelType = type[pydantic_v2.BaseModel]


JSON_STRING = {"type": "string", "contentMediaType": "application/json", "contentSchema": {}}


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


def dto_field_schema(model: type[pydantic_v2.BaseModel]) -> Any:
    def handler() -> Any:
        return None

    handler.__annotations__["return"] = model
    app = Litestar([get("/", return_dto=PydanticDTO[model], sync_to_thread=False)(handler)])  # type: ignore[valid-type]
    (schema,) = app.openapi_schema.components.schemas.values()  # pyright: ignore[reportOptionalMemberAccess]
    return schema


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
) -> None:
    class Model(pydantic_v2.BaseModel):
        field: make_constraint(int, min_length=min_length, max_length=max_length)  # type: ignore[valid-type]

    schema = dto_field_schema(Model).properties["field"]

    assert schema.type == OpenAPIType.ARRAY
    assert schema.items.type == OpenAPIType.INTEGER
    assert schema.min_items == min_length
    assert schema.max_items == max_length


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
) -> None:
    class Modelv2(pydantic_v2.BaseModel):
        set_field: conset(Union[str, int], min_length=1, max_length=10)  # type: ignore[valid-type]
        list_field: conlist(Union[str, int], min_length=1, max_length=10)  # type: ignore[valid-type]

    model_schema = dto_field_schema(Modelv2)

    def _get_schema_type(s: Any) -> OpenAPIType:
        assert isinstance(s, Schema)
        assert isinstance(s.type, OpenAPIType)
        return s.type

    for field_name in ["set_field", "list_field"]:
        schema = model_schema.properties[field_name]

        assert schema.type == OpenAPIType.ARRAY
        assert schema.max_items == 10
        assert schema.min_items == 1
        assert isinstance(schema.items, Schema)
        assert schema.items.one_of is not None

        # https://github.com/litestar-org/litestar/pull/2570#issuecomment-1788122570
        assert {_get_schema_type(s) for s in schema.items.one_of} == {OpenAPIType.STRING, OpenAPIType.INTEGER}

    # set should have uniqueItems always
    assert model_schema.properties["set_field"].unique_items


@pytest.mark.parametrize("annotation", constrained_string_v2)
def test_create_string_constrained_field_schema_pydantic_v2(
    annotation: Any,
) -> None:
    constraint: pydantic_v2.types.StringConstraints = annotation.__metadata__[0]

    class Model(pydantic_v2.BaseModel):
        field: annotation

    schema = dto_field_schema(Model).properties["field"]

    assert schema.type == OpenAPIType.STRING
    assert schema.min_length == constraint.min_length
    assert schema.max_length == constraint.max_length
    assert schema.pattern == constraint.pattern
    if constraint.to_upper:
        assert schema.description == "must be in upper case"
    if constraint.to_lower:
        assert schema.description == "must be in lower case"


@pytest.mark.parametrize("annotation", constrained_bytes_v2)
def test_create_byte_constrained_field_schema_pydantic_v2(
    annotation: Any,
) -> None:
    constraint: annotated_types.Len = annotation.__metadata__[1]

    class Model(pydantic_v2.BaseModel):
        field: annotation

    schema = dto_field_schema(Model).properties["field"]

    assert schema.type == OpenAPIType.STRING
    assert schema.min_length == constraint.min_length
    assert schema.max_length == constraint.max_length


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
        (pydantic_v2.condecimal, {"gt": Decimal("10"), "lt": Decimal("100")}),
        (pydantic_v2.condecimal, {"ge": Decimal("10"), "le": Decimal("100")}),
        (pydantic_v2.condecimal, {"gt": Decimal("10"), "lt": Decimal("100"), "multiple_of": Decimal("5")}),
        (pydantic_v2.condecimal, {"ge": Decimal("10"), "le": Decimal("100"), "multiple_of": Decimal("2")}),
    ],
)
def test_create_numerical_constrained_field_schema_pydantic_v2(
    make_constraint: Any,
    constraint_kwargs: dict[str, Any],
) -> None:
    annotation = make_constraint(**constraint_kwargs)

    class Model(pydantic_v2.BaseModel):
        field: annotation  # type: ignore[valid-type]

    schema = dto_field_schema(Model).properties["field"]

    assert schema.type == OpenAPIType.INTEGER if is_class_and_subclass(annotation, int) else OpenAPIType.NUMBER
    assert schema.exclusive_minimum == constraint_kwargs.get("gt")
    assert schema.minimum == constraint_kwargs.get("ge")
    assert schema.exclusive_maximum == constraint_kwargs.get("lt")
    assert schema.maximum == constraint_kwargs.get("le")
    assert schema.multiple_of == constraint_kwargs.get("multiple_of")


@pytest.mark.parametrize(
    "constraints",
    [
        {"gt": date.today() - timedelta(days=10), "lt": date.today() + timedelta(days=100)},
        {"ge": date.today() - timedelta(days=10), "le": date.today() + timedelta(days=100)},
        {"gt": date.today() - timedelta(days=10), "lt": date.today() + timedelta(days=100)},
        {"ge": date.today() - timedelta(days=10), "le": date.today() + timedelta(days=100)},
    ],
)
def test_create_date_constrained_field_schema_pydantic_v2(
    constraints: dict[str, Any],
) -> None:
    class Model(pydantic_v2.BaseModel):
        field: pydantic_v2.condate(**constraints)  # type: ignore[valid-type]

    schema = dto_field_schema(Model).properties["field"]
    assert schema.type == OpenAPIType.STRING
    assert schema.format == OpenAPIFormat.DATE

    if gt := constraints.get("gt"):
        assert date.fromtimestamp(schema.exclusive_minimum) == gt
    if ge := constraints.get("ge"):
        assert date.fromtimestamp(schema.minimum) == ge
    if lt := constraints.get("lt"):
        assert date.fromtimestamp(schema.exclusive_maximum) == lt
    if le := constraints.get("le"):
        assert date.fromtimestamp(schema.maximum) == le


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
) -> None:
    class Model(pydantic_v2.BaseModel):
        field: annotation

    assert dto_field_schema(Model).properties["field"]


def test_spec_generation() -> None:
    schemas = pydantic_document(PydanticPerson)["components"]["schemas"]

    expected = {
        "properties": {
            "first_name": {"title": "First Name", "type": "string"},
            "last_name": {"title": "Last Name", "type": "string"},
            "id": {"title": "Id", "type": "string"},
            "optional": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Optional"},
            "complex": {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": {"type": "string"}},
                },
                "title": "Complex",
            },
            "union": {"anyOf": [{"type": "integer"}, {"items": {"type": "string"}, "type": "array"}], "title": "Union"},
            "pets": {
                "anyOf": [{"items": {"$ref": "#/components/schemas/DataclassPet"}, "type": "array"}, {"type": "null"}],
                "title": "Pets",
            },
        },
        "type": "object",
        "required": ["first_name", "last_name", "id", "optional", "complex", "union"],
        "title": "PydanticPerson",
    }
    assert schemas["PydanticPerson"] == expected
    assert not {"PydanticPerson-Input", "PydanticPerson-Output"} & set(schemas)
    assert schemas["DataclassPet"]["properties"]["species"] == {
        "allOf": [{"$ref": "#/components/schemas/Species"}],
        "default": "Monkey",
    }


def test_spec_generation_pydantic_dataclass() -> None:
    @post("/")
    def handler(data: JSONBody[PydanticDataclassPerson]) -> PydanticDataclassPerson:
        return data

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema

        assert schema.to_schema()["components"]["schemas"]["PydanticDataclassPerson"] == {
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "id": {"type": "string"},
                "optional": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "complex": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                },
                "union": {"anyOf": [{"type": "integer"}, {"items": {"type": "string"}, "type": "array"}]},
                "pets": {
                    "anyOf": [
                        {
                            "items": {"$ref": "#/components/schemas/DataclassPet"},
                            "type": "array",
                        },
                        {"type": "null"},
                    ]
                },
            },
            "type": "object",
            "required": ["first_name", "last_name", "id", "optional", "complex", "union"],
            "title": "PydanticDataclassPerson",
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
    lookup_schema = schema["components"]["schemas"]["Lookup"]["properties"]

    assert lookup_schema["id"] == {
        "description": "A unique identifier",
        "examples": ["31"],
        "example": "e4eaaaf2-d142-11e1-b3e4-080027620cdd",
        "maxLength": 16,
        "minLength": 12,
        "title": "Id",
        "type": "string",
    }
    assert lookup_schema["with_title"] == {"title": "WITH_title", "type": "string"}
    assert lookup_schema["with_extra_title"] == {"title": "WITH_extra", "type": "string"}
    assert lookup_schema["without_duplicates"] == {
        "type": "array",
        "items": {"type": "string"},
        "uniqueItems": True,
        "title": "Without Duplicates",
    }


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
    lookup_schema = schema["components"]["schemas"]["Model"]["properties"]

    assert lookup_schema["foo"]["examples"] == ["32"]
    assert "examples" not in lookup_schema["bar"]
    response = schema["paths"]["/example"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["allOf"] == [{"$ref": "#/components/schemas/Model"}]
    assert response["examples"]


def test_json_schema_extra_callable_is_applied() -> None:
    def describe(schema: dict[str, Any]) -> None:
        schema["description"] = "described"

    class Model(pydantic_v2.BaseModel):
        field: str = pydantic_v2.Field(json_schema_extra=describe)

    schema = pydantic_document(Model, request=False)["components"]["schemas"]["Model"]

    assert schema["properties"]["field"] == {"description": "described", "title": "Field", "type": "string"}


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
    assert schemas["RequestWithAlias"] == {
        "properties": {request_key: {"title": "Second", "type": "string"}},
        "type": "object",
        "required": [request_key],
        "title": "RequestWithAlias",
    }
    response_key = "first"
    assert schemas["ResponseWithAlias"] == {
        "properties": {response_key: {"title": "First", "type": "string"}},
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
    assert schemas["RequestWithAlias"] == {
        "properties": {request_key: {"title": "Second", "type": "string"}},
        "type": "object",
        "required": [request_key],
        "title": "RequestWithAlias",
    }
    response_key = "second"
    assert schemas["ResponseWithAlias"] == {
        "properties": {response_key: {"title": "Second", "type": "string"}},
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

    value = pydantic_document(Model, response=False)["components"]["schemas"]["Model"]["properties"]["value"]

    assert value["description"] == "description"
    assert value["title"] == "title"
    assert value["example"] == "example"


def test_create_schema_for_field_v2_examples() -> None:
    class Model(pydantic_v2.BaseModel):
        value: str = pydantic_v2.Field(
            title="title", description="description", max_length=16, json_schema_extra={"examples": ["example"]}
        )

    value = pydantic_document(Model, response=False)["components"]["schemas"]["Model"]["properties"]["value"]

    assert value["description"] == "description"
    assert value["title"] == "title"
    assert value["examples"] == ["example"]


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
    schemas = pydantic_document(module.Foo, response=False)["components"]["schemas"]
    assert schemas["Foo"]["properties"] == {"foo": {"type": "integer", "title": "Foo"}}


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
    properties = pydantic_document(module.Model, response=False)["components"]["schemas"]["Model"]["properties"]
    assert properties["dict_default"]["default"] == properties["dict_default_in_field"]["default"] == {}
    assert properties["list_default"]["default"] == properties["list_default_in_field"]["default"] == []
    assert "default" not in properties["dict_default_in_factory"]
    assert "default" not in properties["list_default_in_factory"]


@pytest.mark.parametrize(
    "annotation",
    [
        pydantic_v2.EmailStr,
        pydantic_v2.NameEmail,
        pydantic_v2.AnyUrl,
        pydantic_v2.AnyHttpUrl,
        pydantic_v2.HttpUrl,
        pydantic_v2.IPvAnyAddress,
        pydantic_v2.IPvAnyInterface,
        pydantic_v2.IPvAnyNetwork,
        pydantic_v2.Json,
        pydantic_v2.SecretStr,
        pydantic_v2.SecretBytes,
        pydantic_v2.ByteSize,
        pydantic_v2.PastDate,
        pydantic_v2.FutureDate,
        pydantic_v2.PastDatetime,
        pydantic_v2.FutureDatetime,
        pydantic_v2.AwareDatetime,
        pydantic_v2.NaiveDatetime,
    ],
)
def test_pydantic_types_outside_models_match_their_schema_inside_models(annotation: Any) -> None:
    class Model(pydantic_v2.BaseModel):
        value: annotation

    def accepts(value: Any, data: Any) -> None:
        return None

    def returns() -> Any:
        return None

    def returns_model() -> Any:
        return None

    accepts.__annotations__ = {"value": FromQuery[annotation], "data": JSONBody[Model], "return": None}  # type: ignore[misc]
    returns.__annotations__ = {"return": annotation}
    returns_model.__annotations__ = {"return": Model}
    app = Litestar(
        [
            post("/", sync_to_thread=False)(accepts),
            get("/", sync_to_thread=False)(returns),
            get("/model", sync_to_thread=False)(returns_model),
        ]
    )
    document = app.openapi_schema.to_schema()
    schemas = document["components"]["schemas"]

    def inside(mode: str) -> dict[str, Any]:
        field = dict(schemas.get(f"Model-{mode}", schemas.get("Model"))["properties"]["value"])
        assert field.pop("title") == "Value"
        return field

    adapter = pydantic_v2.TypeAdapter(annotation)
    parameter = document["paths"]["/"]["post"]["parameters"][0]["schema"]
    response = document["paths"]["/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    validation = adapter.json_schema(mode="validation", schema_generator=_RegisteredFormatsJsonSchema)
    serialization = adapter.json_schema(mode="serialization", schema_generator=_RegisteredFormatsJsonSchema)
    assert parameter == inside("Input") == validation
    assert response == inside("Output") == serialization


class OpaqueUrl(pydantic_v2.AnyUrl):
    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls)


@pytest.mark.parametrize(
    "annotation, mode, expected",
    [
        (Optional[pydantic_v2.Json], "serialization", {}),
        (Optional[pydantic_v2.Json], "validation", {**JSON_STRING, "type": ["string", "null"]}),
        (OpaqueUrl, "validation", {}),
        (Optional[OpaqueUrl], "serialization", {}),
    ],
)
def test_pydantic_types_that_accept_anything(annotation: Any, mode: Any, expected: dict[str, Any]) -> None:
    creator = SchemaCreator(plugins=[PydanticSchemaPlugin()], schema_mode=mode)

    assert creator.for_field_definition(FieldDefinition.from_annotation(annotation)).to_schema() == expected


@pytest.mark.parametrize("prefer_alias, name", [(True, "prop_two"), (False, "property_two")])
def test_create_for_computed_field(prefer_alias: bool, name: str) -> None:
    class Sample(pydantic_v2.BaseModel):
        property_one: str

        @pydantic_v2.computed_field(description="a description", title="a title", alias="prop_two")
        def property_two(self) -> bool:
            return True

    plugins = [PydanticPlugin(prefer_alias=prefer_alias)]
    schema = pydantic_document(Sample, request=False, plugins=plugins)["components"]["schemas"]["Sample"]

    assert schema["required"] == ["property_one", name]
    assert schema["properties"] == {
        "property_one": {"type": "string", "title": "Property One"},
        name: {"type": "boolean", "title": "a title", "description": "a description", "readOnly": True},
    }


def test_ip_types_use_registered_formats() -> None:
    class Model(pydantic_v2.BaseModel):
        address_v4: IPv4Address
        interface_v4: IPv4Interface
        network_v4: IPv4Network
        interface_v6: IPv6Interface
        network_v6: IPv6Network
        any_address: pydantic_v2.IPvAnyAddress
        any_interface: pydantic_v2.IPvAnyInterface
        any_network: pydantic_v2.IPvAnyNetwork

    @get("/")
    async def handler(network: FromQuery[pydantic_v2.IPvAnyNetwork]) -> Model:
        raise NotImplementedError

    document = Litestar([handler]).openapi_schema.to_schema()
    properties = document["components"]["schemas"]["Model"]["properties"]
    cidr = {"anyOf": [{"type": "string", "format": "ipv4-cidr"}, {"type": "string", "format": "ipv6-cidr"}]}

    assert {name: {k: v for k, v in schema.items() if k != "title"} for name, schema in properties.items()} == {
        "address_v4": {"type": "string", "format": "ipv4"},
        "interface_v4": {"type": "string", "format": "ipv4-cidr"},
        "network_v4": {"type": "string", "format": "ipv4-cidr"},
        "interface_v6": {"type": "string", "format": "ipv6-cidr"},
        "network_v6": {"type": "string", "format": "ipv6-cidr"},
        "any_address": {"anyOf": [{"type": "string", "format": "ipv4"}, {"type": "string", "format": "ipv6"}]},
        "any_interface": cidr,
        "any_network": cidr,
    }
    assert document["paths"]["/"]["get"]["parameters"][0]["schema"] == cidr


def test_aliased_ip_types_use_registered_formats() -> None:
    Network = TypeAliasType("Network", IPv4Network)
    AnyNetwork = TypeAliasType("AnyNetwork", pydantic_v2.IPvAnyNetwork)

    class Model(pydantic_v2.BaseModel):
        network: Network
        any_network: AnyNetwork

    @get("/")
    async def handler() -> Model:
        raise NotImplementedError

    schemas = Litestar([handler]).openapi_schema.to_schema()["components"]["schemas"]

    assert schemas["Network"] == {"type": "string", "format": "ipv4-cidr"}
    assert schemas["AnyNetwork"] == {
        "anyOf": [{"type": "string", "format": "ipv4-cidr"}, {"type": "string", "format": "ipv6-cidr"}]
    }


def test_pydantic_dto_forbid_documents_additional_properties() -> None:
    class ForbidModel(pydantic_v2.BaseModel):
        model_config = pydantic_v2.ConfigDict(extra="forbid")
        value: int

    @post("/", dto=PydanticDTO[ForbidModel], return_dto=None)
    async def handler(data: JSONBody[ForbidModel]) -> None:
        return None

    document = Litestar([handler]).openapi_schema.to_schema()
    ref = document["paths"]["/"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]

    assert document["components"]["schemas"][ref.rsplit("/", 1)[-1]]["additionalProperties"] is False
