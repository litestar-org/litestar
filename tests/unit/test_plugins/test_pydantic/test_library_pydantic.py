# pyright: reportUnnecessaryTypeIgnoreComment=false

import dataclasses
import datetime
import decimal
import enum
import json
import runpy
import sys
import uuid
from collections.abc import Callable
from typing import Annotated, Any, Generic, Literal, NewType, Optional, TypeVar, Union, cast

import attrs
import msgspec
import pydantic
import pytest
from pydantic import (
    AliasChoices,
    ConfigDict,
    Field,
    Json,
    RootModel,
    TypeAdapter,
    WithJsonSchema,
    WrapSerializer,
    computed_field,
)
from pydantic.json_schema import (
    CoreRef,
    GenerateJsonSchema,
    PydanticJsonSchemaWarning,
    SkipJsonSchema,
    _DefinitionsRemapping,
    models_json_schema,
)
from pydantic_core import core_schema
from typing_extensions import TypeAliasType, TypedDict

from litestar import Litestar, get, post
from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.schema_generation.library import LibraryRun
from litestar._openapi.schema_generation.library.converter import json_schema_to_spec
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar._openapi.schema_generation.schema import SchemaCreator
from litestar.dto import DataclassDTO, dto_field
from litestar.exceptions import ImproperlyConfiguredException, LitestarWarning
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Example, OpenAPIFormat, OpenAPIType, Reference, Schema
from litestar.params import Body, FromQuery, JSONBody, KwargDefinition
from litestar.plugins import OpenAPISchemaPlugin
from litestar.plugins.pydantic import PydanticDTO, PydanticInitPlugin, PydanticPlugin, PydanticSchemaPlugin
from litestar.plugins.pydantic.plugins import schema as schema_module
from litestar.plugins.pydantic.plugins._json_schema import LitestarGenerateJsonSchema
from litestar.testing import TestClient
from litestar.typing import FieldDefinition
from tests.helpers import (
    PREFIX,
    Wrapping,
    body_schema,
    components,
    normalise_json_schema,
    recursion_limit,
    response_schema,
    route,
)
from tests.unit.test_plugins.test_pydantic import pydantic_app, pydantic_document

T = TypeVar("T")


class Plain(pydantic.BaseModel):
    x: int


class Other(pydantic.BaseModel):
    y: str


class U(pydantic.BaseModel):
    user_name: str = Field(alias="userName")


class Outer(pydantic.BaseModel):
    u: U


class Page(pydantic.BaseModel, Generic[T]):
    items: list[T]


class Pets(RootModel[list[int]]):
    pass


class Aliased(pydantic.BaseModel):
    both: int = Field(alias="bothAlias")
    validation_only: int = Field(validation_alias="validationOnly")
    serialization_only: int = Field(serialization_alias="serializationOnly")


class PopulateByName(pydantic.BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    first: int = 0
    user_name: str = Field(alias="userName")
    last: int = 0


class NameOnly(pydantic.BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=False)

    user_name: str = Field(alias="userName")


class Choices(pydantic.BaseModel):
    value: int = Field(validation_alias=AliasChoices("a", "b"))  # type: ignore[pydantic-alias]


class SetChild(pydantic.BaseModel, frozen=True):
    x: int


class Sets(pydantic.BaseModel):
    ints: set[int]
    strs: frozenset[str]
    children: set[SetChild]


class Blob(pydantic.BaseModel):
    data: bytes


class Blob64(pydantic.BaseModel):
    model_config = ConfigDict(ser_json_bytes="base64", val_json_bytes="base64")

    data: bytes
    short: pydantic.conbytes(max_length=3)  # type: ignore[valid-type]


class Scalars(pydantic.BaseModel):
    amount: decimal.Decimal
    at: datetime.datetime
    day: datetime.date
    clock: datetime.time
    span: datetime.timedelta
    ident: uuid.UUID


class S(msgspec.Struct):
    s: int


@attrs.define
class A:
    a: int


class Unknown:
    pass


class Hosts(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    struct: S
    attrs_class: A
    maybe: Optional[S] = None
    unknown: Unknown
    callback: Callable[[], int]


class Special(pydantic.BaseModel):
    x: int


class Opaque:
    pass


@dataclasses.dataclass
class SpecialDc:
    x: int


class SpecialTd(TypedDict):
    x: int


class HoldsSpecial(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: Special
    dc: SpecialDc
    td: SpecialTd
    many: list[SpecialDc]
    by_key: dict[str, SpecialTd]
    opaque: Opaque
    maybe: Optional[SpecialDc] = None


class CustomPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation in (Special, Opaque, SpecialDc, SpecialTd, Cat)

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        return Schema(type=OpenAPIType.STRING, description=field_definition.annotation.__name__)


class Named(pydantic.BaseModel):
    __schema_name__ = "IdContainer"

    id: int


class Holder(pydantic.BaseModel):
    named: Named


class NamedAliased(pydantic.BaseModel):
    __schema_name__ = "IdContainer"

    user_name: str = Field(alias="userName")


class NamedTitled(pydantic.BaseModel):
    __schema_name__ = "IdContainer"
    model_config = ConfigDict(title="T")

    id: int


class Color(enum.Enum):
    RED = "red"
    GREEN = "green"


class Paint(pydantic.BaseModel):
    color: Color = Color.RED


@dataclasses.dataclass
class DcPaint:
    color: Color


def model_extra(schema: dict[str, Any], cls: type[Any]) -> None:
    schema["description"] = f"{cls.__name__} described"


def field_extra(schema: dict[str, Any]) -> None:
    schema["examples"] = [42]


class ExtraDict(pydantic.BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"a": 1}]})

    a: int = Field(json_schema_extra=field_extra)


class ExtraCallable(pydantic.BaseModel):
    model_config = ConfigDict(json_schema_extra=model_extra)

    a: int


class Computed(pydantic.BaseModel):
    a: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def double(self) -> int:
        return self.a * 2


class Cat(pydantic.BaseModel):
    kind: Literal["cat"]


class Dog(pydantic.BaseModel):
    kind: Literal["dog"]


class PicksPet(pydantic.BaseModel):
    pet: Annotated[Union[Cat, Dog], Field(discriminator="kind")]


class Node(pydantic.BaseModel):
    children: list["Node"] = []


class Lizard(pydantic.BaseModel):
    kind: Literal["reptile"]
    sub: Literal["lizard"]


class Snake(pydantic.BaseModel):
    kind: Literal["reptile"]
    sub: Literal["snake"]


class NestedPets(pydantic.BaseModel):
    pet: Annotated[Union[Cat, Annotated[Union[Lizard, Snake], Field(discriminator="sub")]], Field(discriminator="kind")]


class Product(pydantic.BaseModel):
    sku: str


class Line(pydantic.BaseModel):
    product: Product


class Order(pydantic.BaseModel):
    lines: list[Line]


ItemA = pydantic.create_model("Item", __module__="app.a", a=(int, ...))
ItemB = pydantic.create_model("Item", __module__="app.b", b=(str, ...))
Incomplete = pydantic.create_model("Incomplete", other=(cast("Any", "Later"), ...))


class SerializationOverride(pydantic.BaseModel):
    model_config = ConfigDict(json_schema_mode_override="serialization")

    child: U


class ValidationOverride(pydantic.BaseModel):
    model_config = ConfigDict(json_schema_mode_override="validation")

    child: U


@pydantic.dataclasses.dataclass
class Measure:
    value: int = Field(ge=0)


class StructRoot(RootModel[Any]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: S


class HoldsStructRoot(pydantic.BaseModel):
    held: StructRoot


class NamedPerson(pydantic.BaseModel):
    __schema_name__ = "Person"

    user_name: str = Field(alias="userName")


class UCarrier(msgspec.Struct):
    u: U


class PersonCarrier(msgspec.Struct):
    person: NamedPerson


class UVia(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    carrier: UCarrier


class PersonVia(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    carrier: PersonCarrier


class NamedComputed(pydantic.BaseModel):
    __schema_name__ = "Person"

    a: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def double(self) -> int:
        return self.a * 2


@dataclasses.dataclass
class DcHolder:
    person: NamedComputed


@pydantic.dataclasses.dataclass(config=ConfigDict(populate_by_name=True))
class DcByName:
    user_name: str = Field(alias="userName")


@pydantic.with_config(ConfigDict(populate_by_name=True))
class TdByName(TypedDict):
    user_name: Annotated[str, Field(alias="userName")]


@dataclasses.dataclass
class StdlibDcAliased:
    user_name: str = Field(alias="userName")


class NestsByName(pydantic.BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dc: DcByName
    td: TdByName
    stdlib: StdlibDcAliased


class NamedExtraTitle(pydantic.BaseModel):
    __schema_name__ = "IdContainer"
    model_config = ConfigDict(json_schema_extra={"title": "From extra"})

    id: int


class InheritingPydanticPlugin(PydanticSchemaPlugin):
    pass


class PatchingPydanticPlugin(PydanticSchemaPlugin):
    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        schema = super().to_openapi_schema(field_definition, schema_creator)
        schema.description = "patched"
        return schema


class ReplacingPydanticPlugin(PydanticSchemaPlugin):
    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        if field_definition.annotation is Plain:
            return Schema(type=OpenAPIType.STRING, description="replaced")
        return super().to_openapi_schema(field_definition, schema_creator)


class HoldsPlain(pydantic.BaseModel):
    plain: Plain


@dataclasses.dataclass
class DcHoldsPlain:
    plain: Plain


@pydantic.dataclasses.dataclass
class PydanticFieldDefaults:
    undefined: int = Field(description="no default")
    described: int = Field(default=1, description="hi")
    factory: list[int] = Field(default_factory=list)


class Features(pydantic.BaseModel):
    extra_dict: ExtraDict
    extra_callable: ExtraCallable
    pet: Annotated[Union[Cat, Dog], Field(discriminator="kind")]
    node: Node
    page: Page[int]
    pets: Pets
    measure: Measure


@pytest.fixture()
def generator_inputs(monkeypatch: pytest.MonkeyPatch) -> list[list[tuple[Any, str]]]:
    calls: list[list[tuple[Any, str]]] = []
    original = LitestarGenerateJsonSchema.generate_definitions

    def spy(self: LitestarGenerateJsonSchema, inputs: Any) -> Any:
        calls.append([(key.annotation, mode) for key, mode, _ in inputs])
        return original(self, inputs)

    monkeypatch.setattr(LitestarGenerateJsonSchema, "generate_definitions", spy)
    return calls


@pytest.mark.parametrize("library_models", [True, False])
@pytest.mark.parametrize("plugin", [PydanticSchemaPlugin(), InheritingPydanticPlugin(), PatchingPydanticPlugin()])
def test_models_are_always_deferred_to_pydantic_scalars_are_not(
    plugin: PydanticSchemaPlugin, library_models: bool
) -> None:
    creator = SchemaCreator(plugins=[plugin], library_models=library_models)

    for model in (Plain, Pets, Page[int]):
        result = plugin.to_openapi_schema(FieldDefinition.from_annotation(model), creator)
        assert isinstance(result, Reference)
        assert creator.schema_registry.library.is_placeholder(result)
    email = plugin.to_openapi_schema(FieldDefinition.from_annotation(pydantic.EmailStr), creator)
    assert isinstance(email, Schema)
    assert (email.type, email.format) == (OpenAPIType.STRING, OpenAPIFormat.EMAIL)


def test_subclass_overriding_to_openapi_schema_keeps_its_change() -> None:
    patched = pydantic_document(Plain, request=False, plugins=[PatchingPydanticPlugin()])
    assert components(patched) == components(pydantic_document(Plain, request=False))
    assert response_schema(patched) == {"$ref": f"{PREFIX}Plain", "description": "patched"}

    replaced = components(pydantic_document(HoldsPlain, request=False, plugins=[ReplacingPydanticPlugin()]))
    assert set(replaced) == {"HoldsPlain"}
    assert replaced["HoldsPlain"]["properties"] == {"plain": {"type": "string", "description": "replaced"}}


def test_pydantic_models_inside_dto_transfer_models_are_deferred() -> None:
    @get("/", return_dto=PydanticDTO[Plain], sync_to_thread=False)
    def handler() -> Plain:
        return Plain(x=1)

    @get("/holder", return_dto=DataclassDTO[DcHoldsPlain], sync_to_thread=False)
    def holder() -> DcHoldsPlain:
        return DcHoldsPlain(plain=Plain(x=1))

    schemas = components(Litestar([handler, holder]).openapi_schema.to_schema())

    assert set(schemas) == {"HandlerPlainResponseBody", "HolderDcHoldsPlainResponseBody", "Plain"}
    assert schemas["HandlerPlainResponseBody"]["properties"] == {"x": {"type": "integer"}}
    assert schemas["HolderDcHoldsPlainResponseBody"]["properties"] == {"plain": {"$ref": f"{PREFIX}Plain"}}
    assert schemas["Plain"] == components(pydantic_document(Plain, request=False))["Plain"]


class FieldExample(pydantic.BaseModel):
    x: int = Field(json_schema_extra={"example": 1})


def test_dto_route_keeps_the_model_json_schema_extra() -> None:
    @get("/dto", return_dto=PydanticDTO[FieldExample], sync_to_thread=False)
    def with_dto() -> FieldExample:
        return FieldExample(x=1)

    @get("/plain", sync_to_thread=False)
    def plain() -> FieldExample:
        return FieldExample(x=1)

    schemas = components(Litestar([with_dto, plain]).openapi_schema.to_schema())

    assert FieldExample.model_fields["x"].json_schema_extra == {"example": 1}
    assert schemas["WithDtoFieldExampleResponseBody"]["properties"]["x"]["examples"] == [1]
    assert schemas["FieldExample"]["properties"]["x"] == {"example": 1, "title": "X", "type": "integer"}


def test_pydantic_dataclass_field_defaults_are_not_documented() -> None:
    schemas = components(pydantic_document(PydanticFieldDefaults, response=False))

    assert schemas["PydanticFieldDefaults"]["properties"] == {
        "undefined": {"type": "integer"},
        "described": {"type": "integer"},
        "factory": {"type": "array", "items": {"type": "integer"}},
    }


def test_one_generator_pass_per_round(generator_inputs: list[list[tuple[Any, str]]]) -> None:
    assert Litestar([route(JSONBody[Plain], Plain, "/plain"), route(JSONBody[Other], Other, "/other")]).openapi_schema

    assert len(generator_inputs) == 1
    assert sorted(generator_inputs[0], key=repr) == sorted(
        [(Plain, "validation"), (Plain, "serialization"), (Other, "validation"), (Other, "serialization")], key=repr
    )


def test_mode_split_only_when_schemas_differ() -> None:
    plain = pydantic_document(Plain)
    assert components(plain) == {
        "Plain": {
            "properties": {"x": {"title": "X", "type": "integer"}},
            "required": ["x"],
            "title": "Plain",
            "type": "object",
        }
    }
    assert body_schema(plain) == response_schema(plain) == {"$ref": f"{PREFIX}Plain"}

    aliased = components(pydantic_document(U))
    assert aliased == {
        "U-Input": {
            "properties": {"userName": {"title": "Username", "type": "string"}},
            "required": ["userName"],
            "title": "U",
            "type": "object",
        },
        "U-Output": {
            "properties": {"user_name": {"title": "User Name", "type": "string"}},
            "required": ["user_name"],
            "title": "U",
            "type": "object",
        },
    }

    outer = pydantic_document(Outer)
    assert set(components(outer)) == {"Outer-Input", "Outer-Output", "U-Input", "U-Output"}
    assert components(outer)["Outer-Input"]["properties"] == {"u": {"$ref": f"{PREFIX}U-Input"}}
    assert components(outer)["Outer-Output"]["properties"] == {"u": {"$ref": f"{PREFIX}U-Output"}}
    assert body_schema(outer) == {"$ref": f"{PREFIX}Outer-Input"}
    assert response_schema(outer) == {"$ref": f"{PREFIX}Outer-Output"}


@pytest.mark.parametrize(
    "prefer_alias, response_keys",
    [
        (False, ["both", "validation_only", "serialization_only"]),
        (True, ["bothAlias", "validation_only", "serializationOnly"]),
    ],
)
def test_aliases_follow_runtime_per_mode(prefer_alias: bool, response_keys: list[str]) -> None:
    app = pydantic_app(Aliased, plugins=[PydanticPlugin(prefer_alias=prefer_alias)])
    schemas = components(app.openapi_schema.to_schema())

    assert list(schemas["Aliased-Input"]["properties"]) == ["bothAlias", "validationOnly", "serialization_only"]
    assert list(schemas["Aliased-Output"]["properties"]) == response_keys
    with TestClient(app) as client:
        response = client.post("/", json={"bothAlias": 1, "validationOnly": 2, "serialization_only": 3})
        assert response.status_code == 201
        assert list(response.json()) == response_keys


def test_validate_by_name_documents_every_accepted_key() -> None:
    populate = pydantic_app(PopulateByName, response=False)
    schema = components(populate.openapi_schema.to_schema())["PopulateByName"]
    assert list(schema["properties"]) == ["first", "userName", "user_name", "last"]
    assert schema["properties"]["userName"] == schema["properties"]["user_name"]
    assert "required" not in schema
    assert schema["allOf"] == [{"anyOf": [{"required": ["userName"]}, {"required": ["user_name"]}]}]
    with TestClient(populate) as client:
        assert client.post("/", json={"userName": "a"}).status_code == 201
        assert client.post("/", json={"user_name": "a"}).status_code == 201
        assert client.post("/", json={}).status_code == 400

    name_only = pydantic_app(NameOnly, response=False)
    schema = components(name_only.openapi_schema.to_schema())["NameOnly"]
    assert list(schema["properties"]) == ["user_name"]
    assert schema["required"] == ["user_name"]
    with TestClient(name_only) as client:
        assert client.post("/", json={"user_name": "a"}).status_code == 201
        assert client.post("/", json={"userName": "a"}).status_code == 400

    choices = pydantic_app(Choices, response=False)
    schema = components(choices.openapi_schema.to_schema())["Choices"]
    assert list(schema["properties"]) == ["a", "b"]
    assert schema["allOf"] == [{"anyOf": [{"required": ["a"]}, {"required": ["b"]}]}]
    with TestClient(choices) as client:
        assert client.post("/", json={"a": 1}).status_code == 201
        assert client.post("/", json={"b": 1}).status_code == 201


class AliasedComputed(pydantic.BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(alias="firstName")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def upper(self) -> str:
        return self.first_name.upper()


class SerializedAs(pydantic.BaseModel):
    value: int = Field(alias="a", serialization_alias="b")


@dataclasses.dataclass
class HoldsAliased:
    inner: AliasedComputed


class StructHoldsAliased(msgspec.Struct, rename="camel"):
    inner_value: AliasedComputed


class StrictTimestamp(pydantic.BaseModel):
    model_config = ConfigDict(strict=True)

    at: datetime.datetime


class ValidationAliasOnly(pydantic.BaseModel):
    value: int = Field(validation_alias="v")


@pydantic.dataclasses.dataclass
class AliasedPydanticDataclass:
    value: int = Field(alias="v")


def example_app(model: Any, response: bool = False) -> Litestar:
    def handler(data: Any) -> Any:
        return data if response else None

    handler.__annotations__ = {"data": JSONBody[model], "return": model if response else None}  # type: ignore[misc]
    return Litestar(
        [post("/", sync_to_thread=False)(handler)],
        openapi_config=OpenAPIConfig(title="t", version="1", create_examples=True),
    )


def keys_of(value: Any) -> set[str]:
    if isinstance(value, list):
        return {key for item in value for key in keys_of(item)}
    if isinstance(value, dict):
        return {key for name, item in value.items() for key in (name, *keys_of(item))}
    return set()


@pytest.mark.parametrize(
    ("model", "keys"),
    [
        (AliasedComputed, {"firstName"}),
        (list[AliasedComputed], {"firstName"}),
        (tuple[AliasedComputed, ...], {"firstName"}),
        (HoldsAliased, {"inner", "firstName"}),
        (StructHoldsAliased, {"innerValue", "firstName"}),
        (NameOnly, {"user_name"}),
        (StrictTimestamp, {"at"}),
    ],
)
def test_generated_input_examples_are_accepted_by_the_server(model: Any, keys: set[str]) -> None:
    with TestClient(example_app(model)) as client:
        examples = body_schema(client.get("/schema/openapi.json").json())["examples"]
        assert examples
        for example in examples:
            assert keys_of(example) == keys
            assert client.post("/", json=example).status_code == 201


@pytest.mark.parametrize("model", [ValidationAliasOnly, AliasedPydanticDataclass, list[ValidationAliasOnly]])
def test_no_example_where_polyfactory_cannot_build_the_model(model: Any) -> None:
    document = example_app(model, response=True).openapi_schema.to_schema()

    assert "examples" not in body_schema(document)
    assert "examples" not in response_schema(document)


@pytest.mark.parametrize(
    ("model", "input_examples", "response_keys"),
    [(AliasedComputed, True, {"first_name", "upper"}), (SerializedAs, False, {"value"})],
)
def test_generated_examples_keep_the_response_shape(model: Any, input_examples: bool, response_keys: set[str]) -> None:
    with TestClient(example_app(model, response=True)) as client:
        document = client.get("/schema/openapi.json").json()

    assert ("examples" in body_schema(document)) is input_examples
    assert [set(example) for example in response_schema(document)["examples"]] == [response_keys]


def test_sets_are_documented_without_unique_items() -> None:
    app = pydantic_app(Sets)
    document = app.openapi_schema.to_schema()

    assert components(document)["Sets"]["properties"] == {
        "ints": {"items": {"type": "integer"}, "title": "Ints", "type": "array"},
        "strs": {"items": {"type": "string"}, "title": "Strs", "type": "array"},
        "children": {"items": {"$ref": f"{PREFIX}SetChild"}, "title": "Children", "type": "array"},
    }
    assert "uniqueItems" not in json.dumps(document)
    with TestClient(app) as client:
        payload = {"ints": [1, 1], "strs": ["a", "a"], "children": [{"x": 1}, {"x": 1}]}
        assert client.post("/", json=payload).status_code == 201


def test_bytes_follow_the_json_bytes_setting() -> None:
    app = pydantic_app(Blob)
    assert components(app.openapi_schema.to_schema())["Blob"]["properties"] == {
        "data": {"title": "Data", "type": "string"}
    }
    with TestClient(app) as client:
        response = client.post("/", json={"data": "not base64!!"})
        assert response.status_code == 201
        assert response.json() == {"data": "not base64!!"}

    assert components(pydantic_document(Blob64))["Blob64"]["properties"] == {
        "data": {"format": "base64url", "title": "Data", "type": "string"},
        "short": {"format": "base64url", "maxLength": 3, "title": "Short", "type": "string"},
    }


def test_pydantic_keeps_canonical_scalar_formats() -> None:
    app = pydantic_app(Scalars)
    schemas = components(app.openapi_schema.to_schema())
    request, response = schemas["Scalars-Input"]["properties"], schemas["Scalars-Output"]["properties"]

    adapter = TypeAdapter(decimal.Decimal)
    assert request["amount"] == {**adapter.json_schema(mode="validation"), "title": "Amount"}
    assert response["amount"] == {**adapter.json_schema(mode="serialization"), "title": "Amount"}
    for properties in (request, response):
        assert {name: properties[name].get("format") for name in ("at", "day", "clock", "span", "ident")} == {
            "at": "date-time",
            "day": "date",
            "clock": "time",
            "span": "duration",
            "ident": "uuid",
        }

    payload = {
        "at": "2026-11-19T10:00:00",
        "day": "2026-11-19",
        "clock": "10:00:00",
        "span": "PT1S",
        "ident": str(uuid.uuid4()),
    }
    with TestClient(app) as client:
        assert client.post("/", json={**payload, "amount": 1.5}).status_code == 201
        assert client.post("/", json={**payload, "amount": "1.5"}).status_code == 201
        assert client.post("/", json={**payload, "amount": "nan"}).status_code == 400


def test_non_pydantic_fields_are_handed_back() -> None:
    with pytest.warns(LitestarWarning, match="'callback' of 'Hosts'"):
        document = pydantic_document(Hosts, response=False)

    assert components(document)["Hosts"]["properties"] == {
        "struct": {"$ref": f"{PREFIX}S"},
        "attrs_class": {"$ref": f"{PREFIX}A"},
        "maybe": {"anyOf": [{"$ref": f"{PREFIX}S"}, {"type": "null"}]},
        "unknown": {},
        "callback": {"title": "Callback"},
    }
    assert {"S", "A"} <= set(components(document))


def test_mixed_nesting_round_trip() -> None:
    schemas = components(pydantic_document(UVia, response=False))

    assert set(schemas) == {"UVia", "UCarrier", "U"}
    assert schemas["UVia"]["properties"] == {"carrier": {"$ref": f"{PREFIX}UCarrier"}}
    assert schemas["UCarrier"]["properties"] == {"u": {"$ref": f"{PREFIX}U"}}


def test_custom_plugin_keeps_precedence(generator_inputs: list[list[tuple[Any, str]]]) -> None:
    special = pydantic_document(Special, response=False, plugins=[CustomPlugin()])

    assert body_schema(special) == {"type": "string", "description": "Special"}
    assert all(annotation is not Special for call in generator_inputs for annotation, _ in call)


def test_classes_claimed_by_a_custom_plugin_are_handed_back() -> None:
    document = pydantic_document(HoldsSpecial, plugins=[CustomPlugin()])

    assert components(document) == {
        "HoldsSpecial": {
            "title": "HoldsSpecial",
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Special"},
                "dc": {"type": "string", "description": "SpecialDc"},
                "td": {"type": "string", "description": "SpecialTd"},
                "many": {"type": "array", "items": {"type": "string", "description": "SpecialDc"}, "title": "Many"},
                "by_key": {
                    "type": "object",
                    "additionalProperties": {"type": "string", "description": "SpecialTd"},
                    "title": "By Key",
                },
                "opaque": {"type": "string", "description": "Opaque"},
                "maybe": {"type": ["string", "null"], "description": "SpecialDc"},
            },
            "required": ["model", "dc", "td", "many", "by_key", "opaque"],
        }
    }


def test_discriminated_union_member_claimed_by_a_custom_plugin() -> None:
    schemas = components(pydantic_document(PicksPet, plugins=[CustomPlugin()]))

    assert set(schemas) == {"PicksPet", "Dog"}
    assert schemas["PicksPet"]["properties"]["pet"] == {
        "oneOf": [{"type": "string", "description": "Cat"}, {"$ref": f"{PREFIX}Dog"}],
        "discriminator": {"propertyName": "kind", "mapping": {"dog": f"{PREFIX}Dog"}},
        "title": "Pet",
    }


def test_plugin_wrapping_the_pydantic_plugin_keeps_the_root() -> None:
    wrapped = pydantic_document(Plain, plugins=[Wrapping(PydanticSchemaPlugin(), Plain)])

    assert wrapped == pydantic_document(Plain)
    assert body_schema(wrapped) == {"$ref": f"{PREFIX}Plain"}


def test_component_names_and_titles() -> None:
    named = pydantic_document(Named, request=False)
    assert components(named) == {
        "IdContainer": {
            "properties": {"id": {"title": "Id", "type": "integer"}},
            "required": ["id"],
            "title": "IdContainer",
            "type": "object",
        }
    }
    assert response_schema(named) == {"$ref": f"{PREFIX}IdContainer"}

    holder = components(pydantic_document(Holder, request=False))
    assert set(holder) == {"Holder", "IdContainer"}
    assert holder["Holder"]["properties"] == {"named": {"$ref": f"{PREFIX}IdContainer"}}

    assert set(components(pydantic_document(NamedAliased))) == {"IdContainer-Input", "IdContainer-Output"}
    assert components(pydantic_document(NamedTitled, request=False))["IdContainer"]["title"] == "T"
    assert components(pydantic_document(NamedExtraTitle, request=False))["IdContainer"]["title"] == "From extra"

    keyed = Litestar(
        [route(JSONBody[Annotated[Plain, Body(schema_component_key="Account")]], Plain)]
    ).openapi_schema.to_schema()
    assert set(components(keyed)) == {"Account", "Plain"}
    assert components(keyed)["Account"] == components(keyed)["Plain"]
    assert body_schema(keyed) == {"$ref": f"{PREFIX}Account"}
    assert response_schema(keyed) == {"$ref": f"{PREFIX}Plain"}

    acc = Annotated[U, Body(schema_component_key="Acc")]
    keyed_aliased = Litestar([route(JSONBody[acc], U)]).openapi_schema.to_schema()
    assert set(components(keyed_aliased)) == {"Acc", "U-Output"}
    assert body_schema(keyed_aliased) == {"$ref": f"{PREFIX}Acc"}
    assert list(components(keyed_aliased)["Acc"]["properties"]) == ["userName"]

    keyed_both = Litestar([route(JSONBody[acc], acc)]).openapi_schema.to_schema()
    assert set(components(keyed_both)) == {"Acc-Input", "Acc-Output"}
    assert body_schema(keyed_both) == {"$ref": f"{PREFIX}Acc-Input"}
    assert response_schema(keyed_both) == {"$ref": f"{PREFIX}Acc-Output"}


def test_same_named_classes_are_module_qualified() -> None:
    split = Litestar([route(JSONBody[ItemA], ItemB)]).openapi_schema.to_schema()
    assert components(split) == {
        "app.a.Item": {
            "properties": {"a": {"title": "A", "type": "integer"}},
            "required": ["a"],
            "title": "Item",
            "type": "object",
        },
        "app.b.Item": {
            "properties": {"b": {"title": "B", "type": "string"}},
            "required": ["b"],
            "title": "Item",
            "type": "object",
        },
    }
    assert body_schema(split) == {"$ref": f"{PREFIX}app.a.Item"}
    assert response_schema(split) == {"$ref": f"{PREFIX}app.b.Item"}

    shared = Litestar([route(JSONBody[ItemA], ItemB), route(JSONBody[ItemA], ItemA, "/a")]).openapi_schema.to_schema()
    assert set(components(shared)) == {"app.a.Item", "app.b.Item"}
    assert body_schema(shared, "/a") == response_schema(shared, "/a") == {"$ref": f"{PREFIX}app.a.Item"}


@pytest.mark.parametrize("model, expected", [(Order, {"Order", "Line", "Product"}), (Node, {"Node"})])
def test_identical_modes_share_one_component(model: Any, expected: set[str]) -> None:
    document = pydantic_document(model)

    assert set(components(document)) == expected
    assert body_schema(document) == response_schema(document) == {"$ref": f"{PREFIX}{model.__name__}"}


def test_nested_discriminated_union_keeps_its_one_of() -> None:
    app = pydantic_app(NestedPets, response=False)
    pet = components(app.openapi_schema.to_schema())["NestedPets"]["properties"]["pet"]

    assert "discriminator" not in pet
    assert pet["oneOf"] == [
        {"$ref": f"{PREFIX}Cat"},
        {
            "discriminator": {
                "mapping": {"lizard": f"{PREFIX}Lizard", "snake": f"{PREFIX}Snake"},
                "propertyName": "sub",
            },
            "oneOf": [{"$ref": f"{PREFIX}Lizard"}, {"$ref": f"{PREFIX}Snake"}],
        },
    ]
    with TestClient(app) as client:
        assert client.post("/", json={"pet": {"kind": "reptile", "sub": "snake"}}).status_code == 201


def child_keys(document: dict[str, Any], root: Any) -> list[str]:
    schemas = components(document)
    child = schemas[root["$ref"][len(PREFIX) :]]["properties"]["child"]
    return list(schemas[child["$ref"][len(PREFIX) :]]["properties"])


@pytest.mark.parametrize("model", [SerializationOverride, ValidationOverride])
def test_json_schema_mode_override_with_nested_models(model: Any) -> None:
    request_only = pydantic_document(model, response=False)
    assert child_keys(request_only, body_schema(request_only)) == ["userName"]

    response_only = pydantic_document(model, request=False)
    assert child_keys(response_only, response_schema(response_only)) == ["user_name"]

    app = pydantic_app(model)
    both = app.openapi_schema.to_schema()
    assert child_keys(both, body_schema(both)) == ["userName"]
    assert child_keys(both, response_schema(both)) == ["user_name"]
    with TestClient(app) as client:
        assert client.post("/", json={"child": {"userName": "a"}}).json() == {"child": {"user_name": "a"}}


def test_private_generate_json_schema_contract() -> None:
    assert _DefinitionsRemapping({}, {}).remap_json_schema({"$ref": "#/$defs/x"}) == {"$ref": "#/$defs/x"}
    assert "_build_definitions_remapping" in vars(GenerateJsonSchema)
    assert "_build_definitions_remapping" in vars(LitestarGenerateJsonSchema)
    assert {"definitions_schema", "definition_ref_schema", "get_defs_ref"} <= vars(GenerateJsonSchema).keys()
    configs: list[dict[str, Any]] = []

    class Recording(LitestarGenerateJsonSchema):
        def str_schema(self, schema: core_schema.StringSchema) -> Any:
            configs.append(dict(self._config.config_dict))
            return super().str_schema(schema)

    generator = Recording(LibraryRun(OpenAPIContext(OpenAPIConfig("t", "1"), []), {}), False)
    keys, definitions = generator.generate_definitions(
        [
            ("outer", "validation", Outer.__pydantic_core_schema__),
            ("outer", "serialization", Outer.__pydantic_core_schema__),
            ("by_name", "validation", PopulateByName.__pydantic_core_schema__),
        ]
    )

    assert definitions.keys() == generator.defs_to_core_refs.keys()
    assert {mode for _, mode in generator.defs_to_core_refs.values()} == {"validation", "serialization"}
    assert all(key["$ref"][len("#/$defs/") :] in definitions for key in keys.values())
    assert [config.get("populate_by_name", False) for config in configs] == [False, False, True]
    assert isinstance(generator._core_defs_invalid_for_json_schema, dict)
    assert generator.get_defs_ref((CoreRef(next(iter(generator.defs_to_core_refs.values()))[0]), "validation"))


def test_incomplete_model_names_the_model() -> None:
    with pytest.raises(ImproperlyConfiguredException, match="Incomplete"):
        pydantic_document(Incomplete, response=False)


def test_enums_stay_litestar_components() -> None:
    @post("/", sync_to_thread=False)
    def paint(data: JSONBody[Paint], color: FromQuery[Color]) -> None:
        return None

    @post("/dc", sync_to_thread=False)
    def dc_paint(data: JSONBody[DcPaint]) -> None:
        return None

    app = Litestar([paint, dc_paint])
    document = app.openapi_schema.to_schema()
    schemas = components(document)

    assert set(schemas) == {"Color", "Paint", "DcPaint"}
    assert schemas["Color"] == {"type": "string", "enum": ["red", "green"], "title": "Color"}
    assert schemas["Paint"]["properties"] == {"color": {"allOf": [{"$ref": f"{PREFIX}Color"}], "default": "red"}}
    assert schemas["DcPaint"]["properties"] == {"color": {"$ref": f"{PREFIX}Color"}}
    with TestClient(app) as client:
        assert client.post("/?color=red", json={"color": "red"}).status_code == 201
        assert client.post("/?color=red", json={"color": "blue"}).status_code == 400


def test_model_level_features_pass_through() -> None:
    computed = components(pydantic_document(Computed))
    assert "double" not in computed["Computed-Input"]["properties"]
    assert computed["Computed-Output"]["properties"]["double"] == {
        "readOnly": True,
        "title": "Double",
        "type": "integer",
    }
    assert computed["Computed-Output"]["required"] == ["a", "double"]

    schemas = components(pydantic_document(Features, response=False))
    assert schemas["ExtraDict"]["examples"] == [{"a": 1}]
    assert schemas["ExtraDict"]["properties"]["a"] == {"examples": [42], "title": "A", "type": "integer"}
    assert schemas["ExtraCallable"]["description"] == "ExtraCallable described"
    assert schemas["Features"]["properties"]["pet"] == {
        "discriminator": {"mapping": {"cat": f"{PREFIX}Cat", "dog": f"{PREFIX}Dog"}, "propertyName": "kind"},
        "oneOf": [{"$ref": f"{PREFIX}Cat"}, {"$ref": f"{PREFIX}Dog"}],
        "title": "Pet",
    }
    assert schemas["Node"]["properties"]["children"]["items"] == {"$ref": f"{PREFIX}Node"}
    assert schemas["Features"]["properties"]["page"] == {"$ref": f"{PREFIX}Page_int_"}
    assert schemas["Pets"] == {"items": {"type": "integer"}, "title": "Pets", "type": "array"}
    assert schemas["Measure"]["properties"]["value"] == {"minimum": 0, "title": "Value", "type": "integer"}


def test_validate_by_name_applies_to_nested_dataclasses_and_typed_dicts() -> None:
    app = pydantic_app(NestsByName, response=False)
    schemas = components(app.openapi_schema.to_schema())

    for name in ("DcByName", "TdByName", "StdlibDcAliased"):
        assert list(schemas[name]["properties"]) == ["userName", "user_name"]
        assert "required" not in schemas[name]
        assert schemas[name]["allOf"] == [{"anyOf": [{"required": ["userName"]}, {"required": ["user_name"]}]}]
    with TestClient(app) as client:
        for key in ("userName", "user_name"):
            assert client.post("/", json={"dc": {key: "a"}, "td": {key: "a"}, "stdlib": {key: "a"}}).status_code == 201


def test_root_model_of_a_handed_back_type_keeps_its_component() -> None:
    top = pydantic_document(StructRoot, request=False)
    assert response_schema(top) == {"$ref": f"{PREFIX}StructRoot"}
    assert components(top)["StructRoot"] == {"allOf": [{"$ref": f"{PREFIX}S"}], "title": "StructRoot"}

    nested = components(pydantic_document(HoldsStructRoot, request=False))
    assert nested["HoldsStructRoot"]["properties"] == {"held": {"$ref": f"{PREFIX}StructRoot"}}
    assert nested["StructRoot"] == {"allOf": [{"$ref": f"{PREFIX}S"}], "title": "StructRoot"}


@pytest.mark.parametrize(
    "body, response, expected",
    [
        (UCarrier, U, {"UCarrier", "U-Input", "U-Output"}),
        (UVia, U, {"UVia", "UCarrier", "U-Input", "U-Output"}),
        (PersonCarrier, NamedPerson, {"PersonCarrier", "Person-Input", "Person-Output"}),
        (PersonVia, NamedPerson, {"PersonVia", "PersonCarrier", "Person-Input", "Person-Output"}),
        (DcHolder, NamedComputed, {"DcHolder", "Person-Input", "Person-Output"}),
    ],
)
def test_models_reached_in_later_rounds_share_one_pass(body: Any, response: Any, expected: set[str]) -> None:
    document = Litestar([route(JSONBody[body], response)]).openapi_schema.to_schema()  # type: ignore[misc]

    assert set(components(document)) == expected
    output = next(name for name in expected if name.endswith("-Output"))
    assert response_schema(document) == {"$ref": f"{PREFIX}{output}"}


class Money:
    def __init__(self, value: Any) -> None:
        self.value = value

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> Any:
        return core_schema.no_info_plain_validator_function(
            lambda value: value if isinstance(value, Money) else Money(value),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda money: str(money.value)),
        )


class MoneyPlugin(OpenAPISchemaPlugin):
    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return value is Money

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        return Schema(type=OpenAPIType.STRING, description="money")


MONEY = {"type": "string", "description": "money"}


def unclaimed_field_warnings(recwarn: pytest.WarningsRecorder) -> list[str]:
    return sorted(str(warning.message) for warning in recwarn if issubclass(warning.category, LitestarWarning))


def unclaimed_field_warning(field: str) -> str:
    return (
        f"Pydantic cannot generate a JSON schema for the field {field} and no schema plugin documents its type, "
        "so it is documented as any value"
    )


class Wallet(pydantic.BaseModel):
    amount: Money
    maybe: Optional[Money] = None


class Weird:
    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> Any:
        return core_schema.no_info_plain_validator_function(lambda value: value)


class MixedSlots(pydantic.BaseModel):
    pair: tuple[Money, Weird]
    either: Union[Callable[[], int], Money, None] = None


@dataclasses.dataclass
class DcWallet:
    amount: Money


class TdWallet(TypedDict):
    amount: Money


class ComputedWallet(pydantic.BaseModel):
    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> Money:
        return Money(1)


class HoldsWallets(pydantic.BaseModel):
    dc: DcWallet
    td: TdWallet
    computed: ComputedWallet


class AliasOnlySchemaPlugin(PydanticSchemaPlugin):
    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        return super().to_openapi_schema(field_definition, schema_creator)


class RefToComponent(pydantic.BaseModel):
    foo: Annotated[dict, WithJsonSchema({"$ref": "#/components/schemas/Foo"})]


class RefToLocalDefinition(pydantic.BaseModel):
    model_config = ConfigDict(json_schema_extra={"$defs": {"X": {"type": "integer"}}})

    x: Annotated[int, WithJsonSchema({"$ref": "#/$defs/X"})]


class DtoFieldOnPlainRoute(pydantic.BaseModel):
    id: int = Field(default=0, json_schema_extra=dto_field("read-only"))  # type: ignore[arg-type]
    e: int = Field(default=1, json_schema_extra={**dto_field("read-only"), "examples": [1]})  # type: ignore[dict-item]


class WrappedDefault(pydantic.BaseModel):
    w: Annotated[int, WrapSerializer(lambda value, handler: {"v": handler(value)}, return_type=dict[str, int])] = 0


@pytest.mark.parametrize(
    "plugins, response_keys",
    [
        ([PydanticPlugin(prefer_alias=True), AliasOnlySchemaPlugin()], ["userName"]),
        ([AliasOnlySchemaPlugin(), PydanticPlugin(prefer_alias=True)], ["userName"]),
        ([PydanticInitPlugin(prefer_alias=True), AliasOnlySchemaPlugin()], ["userName"]),
    ],
)
def test_serialization_aliases_follow_the_serializing_plugin(plugins: list[Any], response_keys: list[str]) -> None:
    app = pydantic_app(U, plugins=plugins)
    document = app.openapi_schema.to_schema()

    output = components(document)[response_schema(document)["$ref"][len(PREFIX) :]]
    assert list(output["properties"]) == response_keys
    with TestClient(app) as client:
        assert list(client.post("/", json={"userName": "a"}).json()) == response_keys


@pytest.mark.parametrize(
    "plugins, properties, unclaimed",
    [
        pytest.param(
            [MoneyPlugin()],
            {
                "amount": {**MONEY, "title": "Amount"},
                "maybe": {**MONEY, "type": ["string", "null"], "title": "Maybe"},
            },
            [],
            id="claimed",
        ),
        pytest.param(
            [],
            {"amount": {"title": "Amount"}, "maybe": {"anyOf": [{}, {"type": "null"}], "title": "Maybe"}},
            ["'amount' of 'Wallet'", "'maybe' of 'Wallet'"],
            id="unclaimed-warns-once-per-field",
        ),
    ],
)
def test_type_pydantic_cannot_describe_is_handed_to_the_plugin_claiming_it(
    plugins: list[Any], properties: dict[str, Any], unclaimed: list[str], recwarn: pytest.WarningsRecorder
) -> None:
    app = pydantic_app(Wallet, plugins=plugins)

    assert components(app.openapi_schema.to_schema())["Wallet"]["properties"] == properties
    assert unclaimed_field_warnings(recwarn) == [unclaimed_field_warning(field) for field in unclaimed]
    with TestClient(app) as client:
        assert client.post("/", json={"amount": "5"}).json() == {"amount": "5", "maybe": None}


@pytest.mark.parametrize("model", [RefToComponent, RefToLocalDefinition])
def test_unresolvable_json_schema_reference_names_the_model(model: type[pydantic.BaseModel]) -> None:
    with pytest.raises(ImproperlyConfiguredException, match=model.__name__):
        pydantic_document(model, response=False)


def test_dto_field_metadata_is_left_out_silently(recwarn: pytest.WarningsRecorder) -> None:
    schema = components(pydantic_document(DtoFieldOnPlainRoute, response=False))["DtoFieldOnPlainRoute"]

    assert schema["properties"] == {
        "id": {"type": "integer", "title": "Id", "default": 0},
        "e": {"type": "integer", "title": "E", "default": 1, "examples": [1]},
    }
    assert not [warning for warning in recwarn if issubclass(warning.category, LitestarWarning)]


def test_default_not_matching_the_serialized_type_is_dropped() -> None:
    schemas = components(pydantic_document(WrappedDefault))

    assert schemas["WrappedDefault-Input"]["properties"]["w"]["default"] == 0
    assert "default" not in schemas["WrappedDefault-Output"]["properties"]["w"]


def test_subclass_defining_the_removed_for_pydantic_model_hook_warns() -> None:
    with pytest.warns(LitestarWarning, match="for_pydantic_model") as recorded:

        class Legacy(PydanticSchemaPlugin):
            def for_pydantic_model(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
                return Schema()

    assert [warning.filename for warning in recorded] == [__file__]


def test_only_the_slot_matching_a_claimed_type_is_handed_back() -> None:
    with pytest.warns(LitestarWarning) as recorded:
        schemas = components(pydantic_document(MixedSlots, response=False, plugins=[MoneyPlugin()]))

    money = {"type": "string", "description": "money"}
    assert schemas["MixedSlots"]["properties"]["pair"]["prefixItems"] == [money, {}]
    assert schemas["MixedSlots"]["properties"]["either"]["anyOf"] == [{}, money, {"type": "null"}]
    messages = sorted(str(warning.message) for warning in recorded if issubclass(warning.category, LitestarWarning))
    assert len(messages) == 2
    assert all("matches none of the types schema plugins document in it (Money)" in m for m in messages)
    assert "'either' of 'MixedSlots'" in messages[0]
    assert "'pair' of 'MixedSlots'" in messages[1]


@pytest.mark.parametrize(
    "plugins, money, unclaimed",
    [
        pytest.param([MoneyPlugin()], MONEY, [], id="claimed"),
        pytest.param(
            [],
            {},
            ["'amount' of 'DcWallet'", "'amount' of 'TdWallet'", "'total' of 'ComputedWallet'"],
            id="unclaimed-are-named",
        ),
    ],
)
def test_dataclass_typed_dict_and_computed_fields_are_handed_back(
    plugins: list[Any], money: dict[str, Any], unclaimed: list[str], recwarn: pytest.WarningsRecorder
) -> None:
    schemas = components(pydantic_document(HoldsWallets, request=False, plugins=plugins))

    assert schemas["DcWallet"]["properties"]["amount"] == {**money, "title": "Amount"}
    assert schemas["TdWallet"]["properties"]["amount"] == {**money, "title": "Amount"}
    assert schemas["ComputedWallet"]["properties"]["total"] == {**money, "title": "Total", "readOnly": True}
    assert unclaimed_field_warnings(recwarn) == [unclaimed_field_warning(field) for field in unclaimed]


MoneyAlias = TypeAliasType("MoneyAlias", Money)
MoneyList = TypeAliasType("MoneyList", list[Money])
Box = TypeAliasType("Box", list[T], type_params=(T,))
MoneyNewType = NewType("MoneyNewType", Money)
MoneyListNewType = NewType("MoneyListNewType", MoneyList)


@pytest.mark.parametrize(
    "annotation, value_schema, alias_components",
    [
        (MoneyAlias, MONEY, {}),
        (MoneyList, {"$ref": f"{PREFIX}MoneyList"}, {"MoneyList": {"type": "array", "items": MONEY}}),
        (Box[Money], {"$ref": f"{PREFIX}Box_Money_"}, {"Box_Money_": {"type": "array", "items": MONEY}}),
        (MoneyNewType, {**MONEY, "title": "Value"}, {}),
        (MoneyListNewType, {"$ref": f"{PREFIX}MoneyList"}, {"MoneyList": {"type": "array", "items": MONEY}}),
    ],
)
def test_aliases_of_types_claimed_by_a_custom_plugin_are_handed_back(
    annotation: Any, value_schema: dict[str, Any], alias_components: dict[str, Any], recwarn: pytest.WarningsRecorder
) -> None:
    model = pydantic.create_model("HoldsAlias", value=(annotation, ...))

    schemas = components(pydantic_document(model, response=False, plugins=[MoneyPlugin()]))

    assert schemas == {
        "HoldsAlias": {
            "properties": {"value": value_schema},
            "required": ["value"],
            "title": "HoldsAlias",
            "type": "object",
        },
        **alias_components,
    }
    assert not [warning for warning in recwarn if issubclass(warning.category, LitestarWarning)]


def test_aliases_shared_between_fields_are_handed_back(recwarn: pytest.WarningsRecorder) -> None:
    model = pydantic.create_model("SharesAlias", a=(cast("Any", MoneyList), ...), b=(tuple[MoneyList, MoneyList], ...))

    schemas = components(pydantic_document(model, response=False, plugins=[MoneyPlugin()]))

    money_list = {"$ref": f"{PREFIX}MoneyList"}
    assert schemas == {
        "MoneyList": {"type": "array", "items": MONEY},
        "SharesAlias": {
            "properties": {
                "a": money_list,
                "b": {
                    "type": "array",
                    "prefixItems": [money_list, money_list],
                    "minItems": 2,
                    "maxItems": 2,
                    "title": "B",
                },
            },
            "required": ["a", "b"],
            "title": "SharesAlias",
            "type": "object",
        },
    }
    assert not [warning for warning in recwarn if issubclass(warning.category, LitestarWarning)]


Unhashable = TypeAliasType("Unhashable", Annotated[Money, {"note": "kept"}], type_params=(T,))


def test_generic_alias_with_an_unhashable_value_is_walked(recwarn: pytest.WarningsRecorder) -> None:
    model = pydantic.create_model("HoldsUnhashable", value=(Unhashable[int], ...))

    schemas = components(pydantic_document(model, response=False, plugins=[MoneyPlugin()]))

    assert schemas["HoldsUnhashable"]["properties"]["value"] == MONEY
    assert not [warning for warning in recwarn if issubclass(warning.category, LitestarWarning)]


class NoJsonSchema:
    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> Any:
        return core_schema.any_schema()

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: Any, handler: Any) -> Any:
        raise pydantic.PydanticInvalidForJsonSchema("no JSON schema")


class HoldsNoJsonSchema(pydantic.BaseModel):
    value: NoJsonSchema


class SkipsInvalid(pydantic.BaseModel):
    a: SkipJsonSchema[Optional[HoldsNoJsonSchema]] = None
    b: SkipJsonSchema[Optional[HoldsNoJsonSchema]] = None
    c: int = 0


def test_invalid_definition_nothing_references_is_left_out() -> None:
    schemas = components(pydantic_document(SkipsInvalid, response=False))

    assert schemas == {
        "SkipsInvalid": {
            "type": "object",
            "properties": {"c": {"type": "integer", "default": 0, "title": "C"}},
            "title": "SkipsInvalid",
        }
    }


def test_deep_graph_of_shared_aliases_is_walked_once(recwarn: pytest.WarningsRecorder) -> None:
    alias: Any = Money
    make_alias: Any = TypeAliasType
    for depth in range(40):
        alias = make_alias(f"Shared{depth}", tuple[alias, alias])
    model = pydantic.create_model("HoldsDeepAlias", value=(alias, ...))

    schemas = components(pydantic_document(model, response=False, plugins=[MoneyPlugin()]))

    assert len(schemas) == 41
    assert schemas["Shared0"]["prefixItems"] == [MONEY, MONEY]
    assert not [warning for warning in recwarn if issubclass(warning.category, LitestarWarning)]


@pytest.mark.skipif(sys.version_info < (3, 12), reason="type statement not available before 3.12")
def test_type_statement_aliases_of_claimed_types_are_handed_back(recwarn: pytest.WarningsRecorder) -> None:
    namespace: dict[str, Any] = {"Money": Money}
    exec(
        "type Listed = list[Money]\ntype Tree = dict[str, Tree | Money]\ntype Pair[V] = tuple[V, V]",
        namespace,
    )
    listed, tree, pair = namespace["Listed"], namespace["Tree"], namespace["Pair"]
    model = pydantic.create_model("HoldsTypeAliases", listed=(listed, ...), tree=(tree, ...), pair=(pair[Money], ...))

    schemas = components(pydantic_document(model, response=False, plugins=[MoneyPlugin()]))

    assert schemas["Listed"] == {"type": "array", "items": MONEY}
    assert schemas["Tree"] == {"type": "object", "additionalProperties": {"anyOf": [{"$ref": f"{PREFIX}Tree"}, MONEY]}}
    assert schemas["Pair_Money_"] == {"type": "array", "prefixItems": [MONEY, MONEY], "minItems": 2, "maxItems": 2}
    assert not [warning for warning in recwarn if issubclass(warning.category, LitestarWarning)]


def test_url_types_that_are_not_classes_are_left_out_of_the_supported_types(monkeypatch: pytest.MonkeyPatch) -> None:
    url_alias = Annotated[pydantic.AnyUrl, pydantic.UrlConstraints(allowed_schemes=["http", "https"])]
    monkeypatch.setattr(pydantic.networks, "HttpUrl", url_alias)
    monkeypatch.setattr(pydantic.networks, "AnyHttpUrl", url_alias)

    plugin = runpy.run_path(str(schema_module.__file__))["PydanticSchemaPlugin"]

    assert not plugin.is_plugin_supported_type(dict)
    assert plugin.is_plugin_supported_type(pydantic.AnyUrl)


class StructItem(msgspec.Struct):
    a: int


class StructPage(msgspec.Struct, Generic[T]):
    items: list[T]


class HoldsStructPages(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    page: StructPage[StructItem]
    numbers: Optional[StructPage[int]] = None


def test_generic_classes_handed_back_keep_their_type_arguments() -> None:
    schemas = components(pydantic_document(HoldsStructPages, response=False))

    assert schemas["HoldsStructPages"]["properties"] == {
        "page": {"$ref": f"{PREFIX}StructPage_StructItem_"},
        "numbers": {"anyOf": [{"$ref": f"{PREFIX}StructPage_int_"}, {"type": "null"}]},
    }
    assert schemas["StructPage_StructItem_"]["properties"] == {
        "items": {"type": "array", "items": {"$ref": f"{PREFIX}StructItem"}}
    }
    assert schemas["StructPage_int_"]["properties"] == {"items": {"type": "array", "items": {"type": "integer"}}}


PagesOf = TypeAliasType("PagesOf", list[StructPage[T]], type_params=(T,))
PageOf = TypeAliasType("PageOf", StructPage[T], type_params=(T,))
ItemAlias = TypeAliasType("ItemAlias", StructItem)
ItemPageAlias = TypeAliasType("ItemPageAlias", StructPage[StructItem])
STRUCTS = ConfigDict(arbitrary_types_allowed=True)


def test_generic_aliases_hand_back_their_substituted_type_arguments() -> None:
    model = pydantic.create_model("HoldsPagesOf", __config__=STRUCTS, value=(PagesOf[StructItem], ...))

    schemas = components(pydantic_document(model, response=False))

    assert set(schemas) == {"HoldsPagesOf", "PagesOf_StructItem_", "StructPage_StructItem_", "StructItem"}
    assert schemas["PagesOf_StructItem_"] == {"type": "array", "items": {"$ref": f"{PREFIX}StructPage_StructItem_"}}


Strs = TypeAliasType("Strs", list[StructPage[str]])


@pytest.mark.parametrize("shared_first", [True, False])
def test_shared_alias_content_does_not_depend_on_field_order(shared_first: bool) -> None:
    fields: dict[str, Any] = {"mixed": (tuple[Strs, StructPage[int]], ...), "plain": (Strs, ...)}
    model = pydantic.create_model(
        "OrdersFields", __config__=STRUCTS, **dict(sorted(fields.items(), reverse=shared_first))
    )

    schemas = components(pydantic_document(model, response=False))

    assert schemas["Strs"] == {"type": "array", "items": {"$ref": f"{PREFIX}StructPage_str_"}}
    assert schemas["OrdersFields"]["properties"]["plain"] == {"$ref": f"{PREFIX}Strs"}


def test_different_parametrisations_in_one_field_fall_back_to_the_class() -> None:
    model = pydantic.create_model(
        "HoldsMixedPages", __config__=STRUCTS, value=(tuple[PagesOf[StructItem], StructPage[int]], ...)
    )

    schemas = components(pydantic_document(model, response=False))

    assert set(schemas) == {"HoldsMixedPages", "PagesOf_StructItem_", "StructPage"}
    assert schemas["HoldsMixedPages"]["properties"]["value"]["prefixItems"] == [
        {"$ref": f"{PREFIX}PagesOf_StructItem_"},
        {"$ref": f"{PREFIX}StructPage"},
    ]


@pytest.mark.parametrize(
    "annotation, reference",
    [
        (ItemAlias, "StructItem"),
        (ItemPageAlias, "StructPage_StructItem_"),
        (PageOf[StructItem], "StructPage_StructItem_"),
    ],
)
def test_aliases_of_handed_back_classes_reference_their_component(annotation: Any, reference: str) -> None:
    model = pydantic.create_model("HoldsClassAlias", __config__=STRUCTS, value=(annotation, ...))

    schemas = components(pydantic_document(model, response=False))

    assert schemas["HoldsClassAlias"]["properties"] == {"value": {"$ref": f"{PREFIX}{reference}"}}
    assert schemas["StructItem"] == {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
        "title": "StructItem",
    }


def test_schema_plugin_prefer_alias_warns_and_is_ignored() -> None:
    with pytest.warns(LitestarWarning, match="PydanticPlugin or PydanticInitPlugin"):
        plugin = PydanticSchemaPlugin(prefer_alias=True)
    app = pydantic_app(U, plugins=[plugin])
    document = app.openapi_schema.to_schema()

    assert list(components(document)["U-Output"]["properties"]) == ["user_name"]
    with TestClient(app) as client:
        assert list(client.post("/", json={"userName": "a"}).json()) == ["user_name"]


class DecStruct(msgspec.Struct):
    d: decimal.Decimal


class HoldsDecStruct(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    s: DecStruct


@dataclasses.dataclass
class DecStructDTOModel:
    name: str
    s: DecStruct


@pytest.mark.parametrize("order", [pytest.param(1, id="dto-first"), pytest.param(-1, id="dto-last")])
def test_dto_routes_leave_structs_nested_in_pydantic_models_unchanged(order: int) -> None:
    @post("/dto", dto=DataclassDTO[DecStructDTOModel], sync_to_thread=False)
    def dto(data: JSONBody[DecStructDTOModel]) -> DecStructDTOModel:
        return data

    plain = Litestar([route(JSONBody[HoldsDecStruct], HoldsDecStruct, "/plain")]).openapi_schema.to_schema()
    routes = [dto, route(JSONBody[HoldsDecStruct], HoldsDecStruct, "/plain")]

    document = Litestar(routes[::order]).openapi_schema.to_schema()

    assert document["paths"]["/plain"] == plain["paths"]["/plain"]
    assert {name: components(document)[name] for name in components(plain)} == components(plain)


def link_chain(length: int) -> Any:
    model: Any = int
    for index in reversed(range(length)):
        model = pydantic.create_model(f"Link{index}", next=(cast("Any", Optional[model]), None))
    return model


def test_long_model_chains_are_documented() -> None:
    limit = sys.getrecursionlimit()

    document = pydantic_document(link_chain(60), response=False)

    assert len(components(document)) == 60
    assert sys.getrecursionlimit() == limit


def test_too_deeply_nested_models_raise_a_clean_error() -> None:
    limit = sys.getrecursionlimit()
    with recursion_limit(max(limit, 50_000)):
        model = link_chain(600)

    with pytest.raises(ImproperlyConfiguredException, match="pydantic schema resolver exceeded the maximum recursion"):
        pydantic_document(model, response=False)
    assert sys.getrecursionlimit() == limit


class ConverterCat(pydantic.BaseModel):
    kind: Literal["cat"]
    lives: int = 9


class ConverterDog(pydantic.BaseModel):
    kind: Literal["dog"]


class PydanticModel(pydantic.BaseModel):
    """doc"""

    model_config = pydantic.ConfigDict(title="PT", json_schema_extra={"examples": [{}]})
    a: Annotated[int, Field(gt=0, le=10, multiple_of=2, description="d", title="T", deprecated=True)] = 1
    s: Annotated[str, Field(min_length=1, max_length=3, pattern="^a")]
    items_: Annotated[list[int], Field(min_length=1, max_length=4)]
    st: set[int]
    fs: frozenset[str]
    tup: tuple[int, str]
    var: tuple[int, ...]
    d: dict[str, int]
    pd: dict[Annotated[str, Field(pattern="^x")], int]
    o: Optional["PydanticModel"] = None
    u: Union[int, str]
    lit: Literal["a", 1]
    colour: Color
    pet: Annotated[Union[ConverterCat, ConverterDog], Field(discriminator="kind")]
    j: Json[list[int]]
    b: bytes
    dec: decimal.Decimal
    dt: datetime.datetime
    tm: datetime.time
    td: datetime.timedelta
    uid: uuid.UUID
    date: datetime.date
    any_: Any
    none: None
    f: float = Field(ge=0.0, lt=1.0)
    ro: int = Field(default=1, json_schema_extra={"readOnly": True})
    al: int = Field(alias="AL", default=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def c(self) -> int:
        return 1


CONVERTER_DEFS = models_json_schema(
    [(PydanticModel, "validation"), (PydanticModel, "serialization")], ref_template="#/$defs/{model}"
)[1]["$defs"]


@pytest.mark.parametrize("name", sorted(CONVERTER_DEFS))
def test_converter_round_trips_pydantic_output(name: str) -> None:
    definition = CONVERTER_DEFS[name]
    dropped: set[str] = set()
    assert json_schema_to_spec(definition, lookup_ref=Reference, dropped=dropped).to_schema() == (
        normalise_json_schema(definition)
    )
    assert not dropped


class ExtraKeysModel(pydantic.BaseModel):
    model_config = ConfigDict(json_schema_extra={"externalDocs": {"url": "https://example.org"}, "$comment": "m"})
    a: int = Field(alias="A", json_schema_extra={"$comment": "f", "x-order": 1})


def test_unsupported_keys_are_dropped_with_one_warning_per_model_and_key() -> None:
    with pytest.warns(LitestarWarning) as record:
        document = pydantic_document(ExtraKeysModel)

    keys = ["$comment", "externalDocs", "x-order"]
    assert sorted(str(warning.message) for warning in record) == [
        f"The JSON schema key {key!r} of 'ExtraKeysModel' cannot be represented in the OpenAPI document and is dropped"
        for key in keys
    ]
    assert not [key for key in keys if key in json.dumps(document)]


class PLeaf(pydantic.BaseModel):
    a: int


class SLeaf(msgspec.Struct):
    a: int


class SOuter(msgspec.Struct):
    p: PLeaf


@dataclasses.dataclass
class DOuter:
    p: PLeaf


class POuter(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)
    s: SLeaf


class PComputed(pydantic.BaseModel):
    a: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def double(self) -> int:
        return 2 * self.a


class SHoldsComputed(msgspec.Struct):
    p: PComputed


@pytest.mark.parametrize(("outer", "inner"), [(SOuter, PLeaf), (DOuter, PLeaf), (POuter, SLeaf)])
def test_cross_library_nesting_without_a_mode_difference_is_not_split(outer: Any, inner: Any) -> None:
    doc = Litestar([route(JSONBody[outer], outer)]).openapi_schema.to_schema()  # type: ignore[misc]
    schemas = components(doc)
    ref = {"$ref": f"{PREFIX}{outer.__name__}"}

    assert set(schemas) == {outer.__name__, inner.__name__}
    assert body_schema(doc) == response_schema(doc) == ref
    assert list(schemas[outer.__name__]["properties"].values()) == [{"$ref": f"{PREFIX}{inner.__name__}"}]


def test_cross_library_mode_difference_splits_the_referrer() -> None:
    doc = Litestar([route(JSONBody[SHoldsComputed], SHoldsComputed)]).openapi_schema.to_schema()
    schemas = components(doc)

    assert set(schemas) == {"SHoldsComputed-Input", "SHoldsComputed-Output", "PComputed-Input", "PComputed-Output"}
    assert body_schema(doc) == {"$ref": f"{PREFIX}SHoldsComputed-Input"}
    assert response_schema(doc) == {"$ref": f"{PREFIX}SHoldsComputed-Output"}
    for suffix in ("-Input", "-Output"):
        assert schemas[f"SHoldsComputed{suffix}"]["properties"]["p"] == {"$ref": f"{PREFIX}PComputed{suffix}"}


class Item(msgspec.Struct):
    a: int


PItem = pydantic.create_model("Item", b=(str, ...))


class PHolder(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)
    item: Item


def returning(annotation: Any, path: str) -> Any:
    def handler() -> Any:
        return None

    handler.__annotations__ = {"return": annotation}
    return get(path, sync_to_thread=False)(handler)


@pytest.mark.parametrize(
    "struct_routes", [pytest.param([], id="no-struct-route"), pytest.param([returning(Item, "/s")], id="struct-route")]
)
def test_name_precedence_follows_resolver_names_in_every_round(struct_routes: list[Any]) -> None:
    doc = Litestar([returning(PHolder, "/h"), returning(PItem, "/p"), *struct_routes]).openapi_schema.to_schema()
    schemas = components(doc)

    assert set(schemas) == {"PHolder", "Item", "Item_2"}
    assert schemas["Item"]["properties"] == {"a": {"type": "integer"}}
    assert schemas["Item_2"]["properties"] == {"b": {"type": "string", "title": "B"}}
    assert schemas["PHolder"]["properties"]["item"] == {"$ref": f"{PREFIX}Item"}
    assert response_schema(doc, "/p", method="get") == {"$ref": f"{PREFIX}Item_2"}


def alternating_chain(depth: int) -> Any:
    child: Any = int
    for level in reversed(range(depth)):
        following = cast("Any", Optional[child])
        child = (
            pydantic.create_model(
                f"P{level}",
                __config__=pydantic.ConfigDict(arbitrary_types_allowed=True),
                v=(int, 0),
                next=(following, None),
            )
            if level % 2
            else msgspec.defstruct(f"S{level}", [("v", int, 0), ("next", following, None)])
        )
    return child


def test_deep_alternating_cross_library_chain_builds() -> None:
    depth = 120
    head = alternating_chain(depth)

    doc = Litestar([route(JSONBody[head], head)]).openapi_schema.to_schema()  # type: ignore[misc,valid-type]

    assert set(components(doc)) == {f"{'P' if level % 2 else 'S'}{level}" for level in range(depth)}
    assert body_schema(doc) == response_schema(doc) == {"$ref": f"{PREFIX}S0"}


ChainItemA = dataclasses.make_dataclass("Item", [("a", int)])
ChainItemA.__module__ = "pkg.a"
ChainItemB = dataclasses.make_dataclass("Item", [("b", int)])
ChainItemB.__module__ = "pkg.b"
ChainTail = msgspec.defstruct("ChainTail", [("item", ChainItemB)])
ChainMiddle = pydantic.create_model(
    "ChainMiddle", __config__=pydantic.ConfigDict(arbitrary_types_allowed=True), tail=(ChainTail, ...)
)
ChainHead = msgspec.defstruct("ChainHead", [("item", ChainItemA), ("middle", ChainMiddle)])


def test_cross_library_chain_documents_every_model() -> None:
    document = Litestar([returning(ChainHead, "/")]).openapi_schema.to_schema()

    assert set(components(document)) == {"ChainHead", "ChainMiddle", "ChainTail", "pkg.a.Item", "pkg.b.Item"}


class KwargModel(pydantic.BaseModel):
    a: Annotated[int, KwargDefinition(title="A", description="a", examples=[Example(value=1)], ge=1)]
    when: Annotated[datetime.date, KwargDefinition(examples=[Example(value=datetime.date(2024, 1, 2))])]
    native: Annotated[int, KwargDefinition(description="kwarg"), pydantic.Field(description="pydantic")]


def test_kwarg_definition_documents_title_description_and_examples_but_no_constraints() -> None:
    properties = components(pydantic_document(KwargModel, response=False))["KwargModel"]["properties"]

    assert properties == {
        "a": {"type": "integer", "title": "A", "description": "a", "examples": [1]},
        "when": {"type": "string", "format": "date", "title": "When", "examples": ["2024-01-02"]},
        "native": {"type": "integer", "title": "Native", "description": "pydantic"},
    }


@pytest.mark.parametrize("version", ["2.10.6", "2.9.0"])
def test_documenting_a_model_requires_pydantic_2_11(version: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pydantic, "VERSION", version)

    with pytest.raises(
        ImproperlyConfiguredException, match=rf"requires pydantic 2\.11 or later, but pydantic {version}"
    ):
        pydantic_document(KwargModel)


def test_old_pydantic_documents_apps_without_pydantic_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pydantic, "VERSION", "2.10.6")

    assert components(pydantic_document(SpecialDc))["SpecialDc"]["properties"] == {"x": {"type": "integer"}}


def test_bytes_default_that_is_not_text_is_left_out() -> None:
    class Blob(pydantic.BaseModel):
        raw: bytes = b"\xff\x00"
        text: bytes = b"ok"

    with pytest.warns(PydanticJsonSchemaWarning, match="not JSON serializable"):
        schema = components(pydantic_app(Blob, request=False).openapi_schema.to_schema())["Blob"]

    assert "default" not in schema["properties"]["raw"]
    assert schema["properties"]["text"]["default"] == "ok"


def test_components_hold_no_placeholder_before_references_are_pointed() -> None:
    class Leaf(pydantic.BaseModel):
        value: int

    @dataclasses.dataclass
    class Holder:
        leaf: Leaf

    context = OpenAPIContext(
        openapi_config=OpenAPIConfig(title="t", version="1"),
        plugins=[*openapi_schema_plugins, PydanticSchemaPlugin()],
    )
    SchemaCreator.from_openapi_context(context).for_field_definition(FieldDefinition.from_annotation(Holder))
    context.schema_registry.library.resolve(context)

    generated = context.schema_registry.generate_components_schemas()

    assert (
        "litestar-library" not in msgspec.json.encode({name: s.to_schema() for name, s in generated.items()}).decode()
    )
    assert sorted(generated) == ["Holder", "Leaf"]


def test_dropped_key_warning_names_a_class_named_like_a_mode_suffix() -> None:
    model = pydantic.create_model(
        "Thing-Output", __config__=pydantic.ConfigDict(json_schema_extra={"x-foo": 1}), a=(int, ...)
    )

    with pytest.warns(LitestarWarning, match="The JSON schema key 'x-foo' of 'Thing-Output' cannot"):
        pydantic_app(model, response=False).openapi_schema.to_schema()
