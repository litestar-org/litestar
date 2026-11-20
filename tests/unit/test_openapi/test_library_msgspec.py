# pyright: reportUnnecessaryTypeIgnoreComment=false

import copy
import dataclasses
import datetime
import decimal
import enum
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from ipaddress import IPv4Address
from pathlib import Path
from re import Pattern
from typing import Annotated, Any, Generic, Literal, NamedTuple, NotRequired, Optional, TypedDict, TypeVar, Union, cast

import annotated_types
import attrs
import msgspec
import msgspec.inspect as mi
import pydantic
import pytest
from msgspec import Meta
from msgspec import _json_schema as js

from litestar import Litestar, get, post
from litestar._openapi.schema_generation.library import _msgspec
from litestar._openapi.schema_generation.library._msgspec import _LitestarTranslator, supports_msgspec_schema
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar._openapi.schema_generation.plugins.dataclass import DataclassSchemaPlugin
from litestar._openapi.schema_generation.plugins.struct import StructSchemaPlugin
from litestar._openapi.schema_generation.plugins.typed_dict import TypedDictSchemaPlugin
from litestar._openapi.schema_generation.schema import SchemaCreator
from litestar.datastructures import UploadFile
from litestar.dto import DataclassDTO, MsgspecDTO
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Example, Reference, Schema
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.params import Body, BodyKwarg, FromQuery, JSONBody, KwargDefinition, QueryParameter
from litestar.plugins import OpenAPISchemaPlugin
from litestar.plugins.attrs import AttrsSchemaPlugin
from litestar.serialization import default_serializer
from litestar.testing import TestClient
from litestar.typing import FieldDefinition
from tests.helpers import (
    PREFIX,
    Wrapping,
    body_schema,
    components,
    document,
    get_components_for_field_definition,
    get_schema_for_field_definition,
    normalise_json_schema,
    recursion_limit,
    response_schema,
)
from tests.models import DataclassPerson, TypedDictPerson

T = TypeVar("T")

DECIMAL_INPUT = {"anyOf": [{"type": "number"}, {"type": "string", "format": "decimal"}]}
DECIMAL_OUTPUT = {"type": "string", "format": "decimal"}


@dataclasses.dataclass
class DcChild:
    n: Annotated[int, Meta(ge=0)]


@dataclasses.dataclass
class DcModel:
    name: Annotated[str, Meta(min_length=1, max_length=5, description="name")]
    child: DcChild
    tags: Annotated[list[str], Meta(max_length=3)] = dataclasses.field(default_factory=list)
    note: Optional[str] = None


class StChild(msgspec.Struct):
    n: Annotated[float, Meta(lt=1.5)]


class StModel(msgspec.Struct, rename="camel", forbid_unknown_fields=True):
    user_name: Annotated[str, Meta(pattern="^a")]
    child: StChild
    max_count: Annotated[int, Meta(le=10)] = 3
    maybe_child: Optional[StChild] = None


class TdChild(TypedDict):
    n: Annotated[int, Meta(multiple_of=2)]


class TdModel(TypedDict):
    name: Annotated[str, Meta(max_length=3)]
    child: TdChild
    note: NotRequired[str]


@attrs.define
class AtChild:
    n: Annotated[int, Meta(gt=0)]


@attrs.define
class AtModel:
    name: Annotated[str, Meta(min_length=2)]
    child: AtChild
    count: int = 1


@dataclasses.dataclass
class SplitInner:
    amount: decimal.Decimal


@dataclasses.dataclass
class SplitPlain:
    x: int


@dataclasses.dataclass
class SplitOuter:
    inner: SplitInner
    plain: SplitPlain


class Cat(msgspec.Struct, tag=True):
    weight: decimal.Decimal


class Dog(msgspec.Struct, tag=True):
    name: str


class Owner(msgspec.Struct):
    pet: Union[Cat, Dog]


@dataclasses.dataclass
class Data:
    v: int


@dataclasses.dataclass
class NamedModel:
    __schema_name__ = "Named"
    v: int


@dataclasses.dataclass
class Holder:
    named: NamedModel


@dataclasses.dataclass
class NamedDecimal:
    __schema_name__ = "Named"
    amount: decimal.Decimal


@dataclasses.dataclass
class Price:
    amount: decimal.Decimal
    described: Annotated[decimal.Decimal, Meta(description="d")]


@dataclasses.dataclass
class DcLiteral:
    mixed: Literal["x", 1]
    ordered: Literal["b", "a"]


class StLiteral(msgspec.Struct):
    mixed: Literal["x", 1]
    ordered: Literal["b", "a"]


@dataclasses.dataclass
class Files:
    path: Path
    ip: IPv4Address
    pattern: Pattern[str]
    upload: Optional[UploadFile]
    described: Annotated[UploadFile, Meta(description="f")]


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


@dataclasses.dataclass
class Paint:
    color: Color = Color.RED


class Money:
    pass


class MoneyPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is Money

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        return Schema(type=OpenAPIType.STRING, format=cast("OpenAPIFormat", "money"))


@dataclasses.dataclass
class SpecialChild:
    x: int


@dataclasses.dataclass
class Special:
    child: SpecialChild


class SpecialPlugin(DataclassSchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is Special

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        return Schema(type=OpenAPIType.STRING)


class PModel(pydantic.BaseModel):
    p: int


@dataclasses.dataclass
class WithPydantic:
    model: PModel


@dataclasses.dataclass
class UnionA:
    a: int


@dataclasses.dataclass
class UnionB:
    b: str


@dataclasses.dataclass
class WithModelUnion:
    ab: Union[UnionA, UnionB]


class MixedEnum(enum.Enum):
    TEXT = "text"
    NUMBER = 1


@dataclasses.dataclass
class WithMixedEnum:
    value: MixedEnum


@dataclasses.dataclass
class Hidden:
    h: int


@dataclasses.dataclass
class WithHidden:
    hidden: "HiddenAlias"  # type: ignore[name-defined]  # noqa: F821


@pydantic.dataclasses.dataclass
class PydanticDataclass:
    a: Annotated[int, pydantic.Field(ge=1)]
    b: Annotated[int, pydantic.Field(alias="bee")] = 0


MONEY = Money()


@dataclasses.dataclass
class DcDefaults:
    root: Path = Path("/srv")
    money: Money = MONEY


class StDefaults(msgspec.Struct):
    root: Path = Path("/srv")
    money: Money = MONEY


@dataclasses.dataclass
class G(Generic[T]):
    v: T


class StG(msgspec.Struct, Generic[T]):
    v: T


def item_class(module: str, field: str) -> Any:
    item = dataclasses.make_dataclass("Item", [(field, int)])
    item.__module__ = module
    return item


ItemA = item_class("pkg.a", "a")
ItemB = item_class("pkg.b", "b")
SameA = item_class("pkg.same", "a")
SameB = item_class("pkg.same", "b")


class User(msgspec.Struct):
    id: int


class UserOut(msgspec.Struct):
    __schema_name__ = "User"
    user: User


@dataclasses.dataclass
class UserWrapper:
    __schema_name__ = "User"
    user: User


class KeyInner(msgspec.Struct):
    id: int


class KeyOuter(msgspec.Struct):
    inner: KeyInner


SpecialItem = item_class("pkg.special", "s")
SpecialItem.__schema_name__ = "Special"
HoldsSpecialAndItem = msgspec.defstruct("HoldsSpecialAndItem", [("special", SpecialItem), ("item", ItemB)])
ClaimedHolder = msgspec.defstruct("ClaimedHolder", [("item", ItemB)])
HoldsItemAndClaimed = msgspec.defstruct("HoldsItemAndClaimed", [("item", ItemA), ("claimed", ClaimedHolder)])


@dataclasses.dataclass
class DcSetDefault:
    tags: frozenset[str] = frozenset("edcba")


class StSetDefault(msgspec.Struct):
    tags: frozenset[str] = frozenset("edcba")


class NT(NamedTuple):
    a: int
    b: str


@dataclasses.dataclass
class WithNamedTuple:
    nt: NT


@dataclasses.dataclass
class Times:
    naive_dt: datetime.datetime
    naive_t: datetime.time
    aware_dt: Annotated[datetime.datetime, Meta(tz=True)]
    naive_only_t: Annotated[datetime.time, Meta(tz=False)]


class SetChild(msgspec.Struct, frozen=True):
    x: int


@dataclasses.dataclass
class DcSets:
    ints: set[int]
    strs: frozenset[str]
    children: set[SetChild]
    unique: Annotated[set[int], Meta(extra_json_schema={"uniqueItems": True})]


class StSets(msgspec.Struct):
    ints: set[int]
    strs: frozenset[str]
    children: set[SetChild]
    unique: Annotated[set[int], Meta(extra_json_schema={"uniqueItems": True})]


@dataclasses.dataclass
class ContractInner:
    i: int


class ContractTD(TypedDict):
    t: str


@dataclasses.dataclass
class ContractOuter:
    inner: ContractInner
    nt: NT
    td: ContractTD
    color: Color


class MyAttrsPlugin(AttrsSchemaPlugin):
    pass


def patching(plugin_type: Any) -> OpenAPISchemaPlugin:
    class Patching(plugin_type):  # type: ignore[misc]
        def to_openapi_schema(
            self, field_definition: FieldDefinition, schema_creator: SchemaCreator
        ) -> Schema | Reference:
            schema = super().to_openapi_schema(field_definition, schema_creator)
            schema.description = "patched"
            return schema  # type: ignore[no-any-return]

    return Patching()


class StExt(msgspec.Struct):
    e: msgspec.msgpack.Ext
    described: Annotated[msgspec.msgpack.Ext, Meta(description="d")]


@dataclasses.dataclass
class DcExt:
    e: msgspec.msgpack.Ext
    described: Annotated[msgspec.msgpack.Ext, Meta(description="d")]


class Claiming(OpenAPISchemaPlugin):
    def __init__(self, claimed: Any) -> None:
        self.claimed = claimed

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is self.claimed

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        return Schema(type=OpenAPIType.STRING, description=self.claimed.__name__)


class HoldsClaimed(msgspec.Struct):
    special: Special
    money: Money
    by_key: dict[str, Special]
    maybe: Optional[Special] = None


@dataclasses.dataclass
class WithAttrs:
    model: AtModel


class BaseStruct(msgspec.Struct):
    __schema_name__ = "BaseName"
    x: int


class ChildStruct(BaseStruct):
    y: str


@dataclasses.dataclass
class Constrained:
    value: Annotated[int, annotated_types.Gt(1), annotated_types.Lt(10)]


def round_trip(model: Any) -> Any:
    @post("/", sync_to_thread=False, signature_namespace={"model": model})
    def handler(data: JSONBody[model]) -> model:  # pyright: ignore[reportInvalidTypeForm]
        return data

    return handler


def body_only(model: Any, path: str = "/") -> Any:
    @post(path, sync_to_thread=False, signature_namespace={"model": model})
    def handler(data: JSONBody[model]) -> None:  # pyright: ignore[reportInvalidTypeForm]
        return None

    return handler


@pytest.mark.parametrize("model", [StModel, DcModel, TdModel, AtModel])
def test_routed_models_match_msgspec_output(model: Any) -> None:
    doc = document([body_only(model)], plugins=(AttrsSchemaPlugin(),))

    expected = msgspec.json.schema_components([model], ref_template=f"{PREFIX}{{name}}")[1]
    assert components(doc) == normalise_json_schema(expected)
    assert body_schema(doc) == {"$ref": f"{PREFIX}{model.__name__}"}


def test_mode_independent_model_is_shared() -> None:
    doc = document([round_trip(DataclassPerson)])
    ref = {"$ref": f"{PREFIX}DataclassPerson"}

    assert body_schema(doc) == response_schema(doc) == ref
    assert {"DataclassPerson", "DataclassPet"} <= components(doc).keys()
    assert "examples" not in components(doc)["DataclassPerson"]
    assert not any(name.endswith(("-Input", "-Output")) for name in components(doc))


def test_mode_independent_model_with_examples_is_shared() -> None:
    doc = document([round_trip(DataclassPerson)], create_examples=True)
    ref = {"$ref": f"{PREFIX}DataclassPerson"}

    for schema in (body_schema(doc), response_schema(doc)):
        assert schema["allOf"] == [ref]
        assert schema["examples"]
    assert {"DataclassPerson", "DataclassPet"} <= components(doc).keys()
    assert "examples" not in components(doc)["DataclassPerson"]
    assert not any(name.endswith(("-Input", "-Output")) for name in components(doc))


def test_mode_dependent_def_and_its_referrers_are_split() -> None:
    doc = document([round_trip(SplitOuter)])
    schemas = components(doc)

    assert set(schemas) == {
        "SplitOuter-Input",
        "SplitOuter-Output",
        "SplitInner-Input",
        "SplitInner-Output",
        "SplitPlain",
    }
    assert body_schema(doc) == {"$ref": f"{PREFIX}SplitOuter-Input"}
    assert response_schema(doc) == {"$ref": f"{PREFIX}SplitOuter-Output"}
    assert schemas["SplitOuter-Input"]["properties"] == {
        "inner": {"$ref": f"{PREFIX}SplitInner-Input"},
        "plain": {"$ref": f"{PREFIX}SplitPlain"},
    }
    assert schemas["SplitOuter-Output"]["properties"] == {
        "inner": {"$ref": f"{PREFIX}SplitInner-Output"},
        "plain": {"$ref": f"{PREFIX}SplitPlain"},
    }
    assert schemas["SplitInner-Input"]["properties"] == {"amount": DECIMAL_INPUT}
    assert schemas["SplitInner-Output"]["properties"] == {"amount": DECIMAL_OUTPUT}

    body_doc = document([body_only(SplitOuter)])
    assert set(components(body_doc)) == {"SplitOuter", "SplitInner", "SplitPlain"}
    assert body_schema(body_doc) == {"$ref": f"{PREFIX}SplitOuter"}


def test_tagged_union_mapping_follows_split() -> None:
    schemas = components(document([round_trip(Owner)]))

    assert set(schemas) == {"Owner-Input", "Owner-Output", "Cat-Input", "Cat-Output", "Dog"}
    for suffix in ("-Input", "-Output"):
        assert schemas[f"Owner{suffix}"]["properties"]["pet"] == {
            "anyOf": [{"$ref": f"{PREFIX}Cat{suffix}"}, {"$ref": f"{PREFIX}Dog"}],
            "discriminator": {
                "propertyName": "type",
                "mapping": {"Cat": f"{PREFIX}Cat{suffix}", "Dog": f"{PREFIX}Dog"},
            },
        }


@pytest.mark.parametrize(
    "model, body_name, response_name, same",
    [(Data, "Data", "Custom", True), (SplitInner, "SplitInner-Input", "Custom", False)],
)
def test_request_name_maps_root_def(model: Any, body_name: str, response_name: str, same: bool) -> None:
    @post("/", sync_to_thread=False, signature_namespace={"model": model})
    def handler(data: JSONBody[model]) -> Annotated[model, Body(schema_component_key="Custom")]:  # pyright: ignore[reportInvalidTypeForm]
        return data

    doc = document([handler])
    schemas = components(doc)

    assert set(schemas) == {body_name, response_name}
    assert body_schema(doc) == {"$ref": f"{PREFIX}{body_name}"}
    assert response_schema(doc) == {"$ref": f"{PREFIX}{response_name}"}
    assert (schemas[body_name] == schemas[response_name]) is same


def test_schema_name_names_class_everywhere() -> None:
    doc = document(
        [
            body_only(NamedModel, "/a"),
            body_only(Holder, "/b"),
            body_only(BaseStruct, "/base"),
            body_only(ChildStruct, "/child"),
        ]
    )
    schemas = components(doc)

    assert set(schemas) == {"Named", "Holder", "BaseName", "ChildStruct"}
    assert schemas["Named"]["title"] == "Named"
    assert schemas["BaseName"]["title"] == "BaseName"
    assert schemas["ChildStruct"]["title"] == "ChildStruct"
    assert set(schemas["ChildStruct"]["properties"]) == {"x", "y"}
    assert body_schema(doc, "/a") == {"$ref": f"{PREFIX}Named"}
    assert body_schema(doc, "/b") == {"$ref": f"{PREFIX}Holder"}
    assert schemas["Holder"]["properties"]["named"] == {"$ref": f"{PREFIX}Named"}

    split = components(document([round_trip(NamedDecimal)]))
    assert set(split) == {"Named-Input", "Named-Output"}
    assert split["Named-Input"]["title"] == split["Named-Output"]["title"] == "Named"


def test_decimal_schema_per_mode_matches_server() -> None:
    handler = round_trip(Price)
    doc = document([handler])
    schemas = components(doc)

    assert schemas["Price-Input"]["properties"] == {
        "amount": DECIMAL_INPUT,
        "described": {**DECIMAL_INPUT, "description": "d"},
    }
    assert schemas["Price-Output"]["properties"] == {
        "amount": DECIMAL_OUTPUT,
        "described": {**DECIMAL_OUTPUT, "description": "d"},
    }

    with TestClient(Litestar([handler])) as client:
        assert client.post("/", json={"amount": 1.5, "described": 2}).status_code == 201
        response = client.post("/", json={"amount": "1.50", "described": "2"})
        assert response.status_code == 201
        assert response.json() == {"amount": "1.50", "described": "2"}
        assert client.post("/", json={"amount": "nope", "described": "2"}).status_code == 400


LITERAL_PROPERTIES = {"mixed": {"enum": ["x", 1]}, "ordered": {"enum": ["b", "a"]}}
EXT_PROPERTIES = {"e": {}, "described": {"description": "d"}}
TIMES_PROPERTIES = {
    "naive_dt": {"type": "string", "format": "date-time"},
    "naive_t": {"type": "string", "format": "time"},
    "aware_dt": {"type": "string", "format": "date-time"},
    "naive_only_t": {"type": "string", "format": "partial-time"},
}


@pytest.mark.parametrize(
    ("model", "properties"),
    [
        pytest.param(DcLiteral, LITERAL_PROPERTIES, id="dataclass-literal-in-declaration-order"),
        pytest.param(StLiteral, LITERAL_PROPERTIES, id="struct-literal-in-declaration-order"),
        pytest.param(StExt, EXT_PROPERTIES, id="struct-msgpack-ext-is-any"),
        pytest.param(DcExt, EXT_PROPERTIES, id="dataclass-msgpack-ext-is-any"),
        pytest.param(Times, TIMES_PROPERTIES, id="datetime-and-time-formats"),
        pytest.param(Constrained, {"value": {"type": "integer"}}, id="annotated-types-not-documented"),
    ],
)
def test_litestar_overrides_of_msgspec_field_schemas(model: Any, properties: dict[str, Any]) -> None:
    assert components(document([body_only(model)]))[model.__name__]["properties"] == properties


def test_custom_types_delegated_to_litestar() -> None:
    def litestar_schema(annotation: Any) -> Any:
        return (
            SchemaCreator(plugins=openapi_schema_plugins)
            .for_field_definition(FieldDefinition.from_annotation(annotation))
            .to_schema()
        )

    properties = components(document([body_only(Files)]))["Files"]["properties"]

    assert properties == {
        "path": litestar_schema(Path),
        "ip": litestar_schema(IPv4Address),
        "pattern": litestar_schema(Pattern),
        "upload": {**litestar_schema(UploadFile), "type": ["string", "null"]},
        "described": {**litestar_schema(UploadFile), "description": "f"},
    }


def test_enum_shared_with_parameter_component() -> None:
    @post("/", sync_to_thread=False)
    def handler(color: FromQuery[Color], data: JSONBody[Paint]) -> None:
        return None

    schemas = components(document([handler]))

    assert [name for name in schemas if "Color" in name] == ["Color"]
    assert schemas["Color"]["enum"] == ["red", "blue"]
    assert schemas["Paint"]["properties"]["color"] == {"allOf": [{"$ref": f"{PREFIX}Color"}], "default": "red"}


def test_user_subclass_of_routed_plugin_keeps_library_schemas() -> None:
    doc = document([body_only(AtModel, "/top"), body_only(WithAttrs, "/nested")], plugins=(MyAttrsPlugin(),))
    schemas = components(doc)

    assert set(schemas) == {"AtModel", "AtChild", "WithAttrs"}
    assert body_schema(doc, "/top") == {"$ref": f"{PREFIX}AtModel"}
    assert schemas["WithAttrs"]["properties"] == {"model": {"$ref": f"{PREFIX}AtModel"}}


@pytest.mark.parametrize(
    "plugin_type, model",
    [
        (StructSchemaPlugin, StChild),
        (DataclassSchemaPlugin, DcChild),
        (TypedDictSchemaPlugin, TdChild),
        (AttrsSchemaPlugin, AtChild),
    ],
)
def test_subclass_overriding_to_openapi_schema_keeps_its_own_schema(
    plugin_type: type[OpenAPISchemaPlugin], model: Any
) -> None:
    plugin = patching(plugin_type)
    field_definition = FieldDefinition.from_annotation(model)
    plugins = [plugin, *openapi_schema_plugins]

    own = plugin.to_openapi_schema(field_definition, SchemaCreator(plugins=plugins, library_models=False))
    assert isinstance(own, Schema)
    assert own.description == "patched"
    assert plugin.to_openapi_schema(field_definition, SchemaCreator(plugins=plugins)) == own

    doc = document([body_only(model)], plugins=(plugin,))
    assert components(doc) == {model.__name__: own.to_schema()}
    assert body_schema(doc) == {"$ref": f"{PREFIX}{model.__name__}"}


def test_class_of_overriding_subclass_nested_in_library_model() -> None:
    schemas = components(document([body_only(WithAttrs)], plugins=(patching(AttrsSchemaPlugin),)))

    assert set(schemas) == {"WithAttrs", "AtModel", "AtChild"}
    assert schemas["WithAttrs"]["properties"] == {"model": {"$ref": f"{PREFIX}AtModel"}}
    assert schemas["AtModel"]["description"] == "patched"
    assert schemas["AtModel"]["properties"]["child"] == {"$ref": f"{PREFIX}AtChild"}
    assert schemas["AtChild"]["description"] == "patched"


def test_tagged_union_member_claimed_by_user_plugin() -> None:
    schemas = components(document([body_only(Owner)], plugins=(Claiming(Cat),)))

    assert set(schemas) == {"Owner", "Dog"}
    assert schemas["Owner"]["properties"] == {
        "pet": {"anyOf": [{"type": "string", "description": "Cat"}, {"$ref": f"{PREFIX}Dog"}]}
    }


def test_classes_claimed_by_user_plugins_are_delegated() -> None:
    schemas = components(document([body_only(HoldsClaimed)], plugins=(SpecialPlugin(), MoneyPlugin())))

    assert schemas == {
        "HoldsClaimed": {
            "title": "HoldsClaimed",
            "type": "object",
            "properties": {
                "special": {"type": "string"},
                "money": {"type": "string", "format": "money"},
                "by_key": {"type": "object", "additionalProperties": {"type": "string"}},
                "maybe": {"type": ["string", "null"]},
            },
            "required": ["special", "money", "by_key"],
        }
    }


@pytest.mark.parametrize("model, inner", [(DcChild, DataclassSchemaPlugin()), (StChild, StructSchemaPlugin())])
def test_plugin_wrapping_a_routed_plugin_keeps_the_root(model: Any, inner: OpenAPISchemaPlugin) -> None:
    wrapped = document([round_trip(model)], plugins=(Wrapping(inner, model),))

    assert wrapped == document([round_trip(model)])


def test_nested_pydantic_model_delegated() -> None:
    schemas = components(document([body_only(WithPydantic)]))

    assert schemas["WithPydantic"]["properties"] == {"model": {"$ref": f"{PREFIX}PModel"}}
    assert schemas["PModel"]["properties"] == {"p": {"title": "P", "type": "integer"}}


@pytest.mark.parametrize(
    "plugin, model",
    [
        (StructSchemaPlugin(), StModel),
        (DataclassSchemaPlugin(), DcModel),
        (TypedDictSchemaPlugin(), TdModel),
        (AttrsSchemaPlugin(), AtModel),
    ],
)
def test_plugins_route_only_in_library_mode(plugin: OpenAPISchemaPlugin, model: Any) -> None:
    field_definition = FieldDefinition.from_annotation(model)
    plugins = [*openapi_schema_plugins, AttrsSchemaPlugin()]

    own = plugin.to_openapi_schema(field_definition, SchemaCreator(plugins=plugins, library_models=False))
    assert isinstance(own, Schema)

    creator = SchemaCreator(plugins=plugins)
    deferred = plugin.to_openapi_schema(field_definition, creator)
    assert isinstance(deferred, Reference)
    assert creator.schema_registry.library.is_placeholder(deferred)


def test_a_model_msgspec_cannot_decode_is_probed_once(monkeypatch: pytest.MonkeyPatch) -> None:
    probed: list[Any] = []

    def probe(annotation: Any) -> bool:
        probed.append(annotation)
        return supports_msgspec_schema(annotation)

    monkeypatch.setattr(_msgspec, "supports_msgspec_schema", probe)
    SchemaCreator(plugins=openapi_schema_plugins).for_field_definition(FieldDefinition.from_annotation(WithModelUnion))

    assert probed.count(WithModelUnion) == 1


@pytest.mark.parametrize(
    "model, field, expected",
    [
        (WithModelUnion, "ab", {"oneOf": [{"$ref": f"{PREFIX}UnionA"}, {"$ref": f"{PREFIX}UnionB"}]}),
        (WithMixedEnum, "value", {"$ref": f"{PREFIX}MixedEnum"}),
        (
            TypedDictPerson,
            "pets",
            {"oneOf": [{"type": "array", "items": {"$ref": f"{PREFIX}DataclassPet"}}, {"type": "null"}]},
        ),
        (WithHidden, "hidden", {"$ref": f"{PREFIX}Hidden"}),
    ],
)
def test_models_msgspec_cannot_decode_fall_back_to_litestar(model: Any, field: str, expected: Any) -> None:
    assert supports_msgspec_schema(model) is False

    @post("/", sync_to_thread=False, signature_namespace={"model": model, "HiddenAlias": Hidden})
    def handler(data: JSONBody[model]) -> None:  # pyright: ignore[reportInvalidTypeForm]
        return None

    schemas = components(document([handler]))
    outer = next(schema for name, schema in schemas.items() if name.endswith(model.__name__))

    assert outer["properties"][field] == expected
    assert outer["required"] == sorted(outer["required"])
    for name in ("UnionA", "UnionB", "DataclassPet", "Hidden"):
        if name in schemas:
            assert schemas[name]["title"] == name


def test_pydantic_and_generic_dataclasses_and_nested_namedtuple() -> None:
    doc = document(
        [
            body_only(PydanticDataclass, "/p"),
            body_only(G[int], "/g"),
            body_only(WithNamedTuple, "/nt"),
        ]
    )
    schemas = components(doc)

    assert schemas["PydanticDataclass"]["properties"] == {
        "a": {"type": "integer"},
        "b": {"type": "integer", "default": 0},
    }
    assert body_schema(doc, "/g") == {"$ref": f"{PREFIX}G_int_"}
    assert schemas["G_int_"]["properties"] == {"v": {"type": "integer"}}
    assert schemas["WithNamedTuple"]["properties"] == {"nt": {"$ref": f"{PREFIX}NT"}}
    assert schemas["NT"] == {
        "title": "NT",
        "type": "array",
        "prefixItems": [{"type": "integer"}, {"type": "string"}],
        "minItems": 2,
        "maxItems": 2,
    }


@pytest.mark.parametrize("model", [DcDefaults, StDefaults])
def test_defaults_documented_as_the_server_encodes_them(model: Any) -> None:
    @get("/", sync_to_thread=False, signature_namespace={"model": model})
    def handler() -> model:  # pyright: ignore[reportInvalidTypeForm]
        return model()

    app = Litestar([handler], plugins=[MoneyPlugin()], type_encoders={Money: lambda _: "1.00"})
    properties = components(app.openapi_schema.to_schema())[model.__name__]["properties"]
    with TestClient(app) as client:
        body = client.get("/").json()

    assert body == {"root": "/srv", "money": "1.00"}
    assert {name: schema["default"] for name, schema in properties.items()} == body

    unencodable = components(document([body_only(model)], plugins=(MoneyPlugin(),)))[model.__name__]["properties"]
    assert unencodable["root"]["default"] == "/srv"
    assert unencodable["money"] == {"type": "string", "format": "money"}


@pytest.mark.parametrize("model", [DcSetDefault, StSetDefault])
def test_set_default_is_documented_in_deterministic_order(model: Any) -> None:
    properties = components(document([body_only(model)]))[model.__name__]["properties"]

    assert properties["tags"]["default"] == ["a", "b", "c", "d", "e"]


@pytest.mark.parametrize(
    ("first", "second", "name"),
    [(SameA, SameB, "pkg.same.Item"), (G[SameA], G[SameB], f"{__name__}.G_pkg.same.Item_")],  # type: ignore[valid-type]
    ids=["class", "generic"],
)
def test_classes_sharing_module_and_qualname_get_distinct_names(first: Any, second: Any, name: str) -> None:
    @post("/", sync_to_thread=False, signature_namespace={"first": first, "second": second})
    def handler(data: JSONBody[first]) -> second:  # pyright: ignore[reportInvalidTypeForm]
        return None

    doc = document([handler])
    schemas = components(doc)

    assert body_schema(doc) == {"$ref": f"{PREFIX}{name}"}
    assert response_schema(doc) == {"$ref": f"{PREFIX}{name}_2"}
    assert {schemas["pkg.same.Item"]["title"], schemas["pkg.same.Item_2"]["title"]} == {"Item"}
    fields = [schemas[f"pkg.same.Item{suffix}"]["properties"] for suffix in ("", "_2")]
    assert fields == [{"a": {"type": "integer"}}, {"b": {"type": "integer"}}]


@pytest.mark.parametrize("generic", [G, StG])
def test_generic_parametrised_with_same_named_classes(generic: Any) -> None:
    doc = document([body_only(generic[ItemA], "/a"), body_only(generic[ItemB], "/b")])
    page_a, page_b = (f"{__name__}.{generic.__name__}_pkg.{module}.Item_" for module in "ab")
    schemas = components(doc)

    assert body_schema(doc, "/a") == {"$ref": f"{PREFIX}{page_a}"}
    assert body_schema(doc, "/b") == {"$ref": f"{PREFIX}{page_b}"}
    assert schemas[page_a]["properties"] == {"v": {"$ref": f"{PREFIX}pkg.a.Item"}}
    assert schemas[page_b]["properties"] == {"v": {"$ref": f"{PREFIX}pkg.b.Item"}}
    assert schemas["pkg.a.Item"]["properties"] == {"a": {"type": "integer"}}
    assert schemas["pkg.b.Item"]["properties"] == {"b": {"type": "integer"}}


@pytest.mark.parametrize("wrapper", [UserOut, UserWrapper])
def test_explicit_schema_name_of_a_nested_class_name_keeps_both_components(wrapper: Any) -> None:
    handler = body_only(wrapper)
    doc = document([handler])
    schemas = components(doc)

    assert set(schemas) == {"User", "User_2"}
    assert body_schema(doc) == {"$ref": f"{PREFIX}User"}
    assert schemas["User"]["properties"] == {"user": {"$ref": f"{PREFIX}User_2"}}
    assert schemas["User_2"]["properties"] == {"id": {"type": "integer"}}
    with TestClient(Litestar([handler])) as client:
        assert client.post("/", json={"user": {"id": 1}}).status_code == 201


def test_component_key_of_a_nested_class_name_keeps_both_components() -> None:
    @post("/keyed", sync_to_thread=False)
    def keyed(data: Annotated[KeyOuter, Body(schema_component_key="KeyInner")]) -> None:
        return None

    doc = document([keyed, body_only(KeyInner, "/inner")])
    schemas = components(doc)

    assert set(schemas) == {"KeyInner", "KeyInner_2"}
    assert body_schema(doc, "/keyed") == {"$ref": f"{PREFIX}KeyInner"}
    assert body_schema(doc, "/inner") == {"$ref": f"{PREFIX}KeyInner_2"}
    assert schemas["KeyInner"]["properties"] == {"inner": {"$ref": f"{PREFIX}KeyInner_2"}}
    assert schemas["KeyInner_2"]["properties"] == {"id": {"type": "integer"}}


def test_explicitly_named_class_does_not_force_qualification() -> None:
    doc = document([body_only(HoldsSpecialAndItem)])
    schemas = components(doc)

    assert set(schemas) == {"HoldsSpecialAndItem", "Special", "Item"}
    assert schemas["HoldsSpecialAndItem"]["properties"] == {
        "special": {"$ref": f"{PREFIX}Special"},
        "item": {"$ref": f"{PREFIX}Item"},
    }


def test_classes_reachable_only_through_delegated_classes_do_not_force_qualification() -> None:
    doc = document([body_only(HoldsItemAndClaimed)], plugins=(Claiming(ClaimedHolder),))
    schemas = components(doc)

    assert set(schemas) == {"HoldsItemAndClaimed", "Item"}
    assert schemas["HoldsItemAndClaimed"]["properties"]["item"] == {"$ref": f"{PREFIX}Item"}
    assert schemas["Item"]["properties"] == {"a": {"type": "integer"}}


@pytest.mark.parametrize("model", [DcSets, StSets])
def test_sets_without_unique_items(model: Any) -> None:
    handler = round_trip(model)
    schemas = components(document([handler]))

    assert set(schemas) == {model.__name__, "SetChild"}
    assert schemas[model.__name__]["properties"] == {
        "ints": {"type": "array", "items": {"type": "integer"}},
        "strs": {"type": "array", "items": {"type": "string"}},
        "children": {"type": "array", "items": {"$ref": f"{PREFIX}SetChild"}},
        "unique": {"type": "array", "items": {"type": "integer"}, "uniqueItems": True},
    }

    payload = {"ints": [1, 1], "strs": ["a", "a"], "children": [{"x": 1}, {"x": 1}], "unique": [1]}
    with TestClient(Litestar([handler])) as client:
        assert client.post("/", json=payload).status_code == 201


@pytest.mark.parametrize(
    "annotation",
    [StModel, DcModel, TdModel, AtModel, DcLiteral, StLiteral, G[int], PydanticDataclass, Annotated[int, {"k": []}]],
)
def test_supports_msgspec_schema_decision(annotation: Any) -> None:
    assert supports_msgspec_schema(annotation) is True


def test_generator_strips_unique_items_from_sets(monkeypatch: pytest.MonkeyPatch) -> None:
    original = js._SchemaGenerator.to_schema

    def with_unique_items(self: js._SchemaGenerator, t: mi.Type, check_ref: bool = True) -> dict[str, Any]:
        schema = original(self, t, check_ref)
        if isinstance(t, (mi.SetType, mi.FrozenSetType)):
            schema["uniqueItems"] = True
        return schema

    monkeypatch.setattr(js._SchemaGenerator, "to_schema", with_unique_items)
    ints = mi.SetType(mi.IntType())
    assert js._SchemaGenerator({}).to_schema(ints)["uniqueItems"] is True

    generator = _msgspec._LitestarSchemaGenerator({}, "validation", (), lambda cls: {}, default_serializer)

    assert generator.to_schema(ints) == {"type": "array", "items": {"type": "integer"}}
    assert generator.to_schema(mi.FrozenSetType(mi.StrType())) == {"type": "array", "items": {"type": "string"}}
    assert generator.to_schema(mi.Metadata(ints, extra_json_schema={"uniqueItems": True})) == {
        "type": "array",
        "items": {"type": "integer"},
        "uniqueItems": True,
    }


def test_private_translator_contract() -> None:
    literal = _LitestarTranslator([Literal["x", 1]]).run()[0]  # type: ignore[no-untyped-call]
    assert isinstance(literal, mi.LiteralType)
    assert list(literal.values) == ["x", 1]

    with pytest.raises(TypeError):
        mi._Translator([Union[UnionA, UnionB]]).run()  # type: ignore[no-untyped-call]

    ge, max_length, tz = _LitestarTranslator(
        [Annotated[int, Meta(ge=1)], Annotated[str, Meta(max_length=2)], Annotated[datetime.datetime, Meta(tz=True)]]
    ).run()  # type: ignore[no-untyped-call]
    assert ge == mi.IntType(ge=1)
    assert max_length == mi.StrType(max_length=2)
    assert tz == mi.DateTimeType(tz=True)


def test_private_collect_component_types_contract() -> None:
    found = js._collect_component_types(mi.multi_type_info([ContractOuter]))

    assert {cls: type(info) for cls, info in found.items()} == {
        ContractOuter: mi.DataclassType,
        ContractInner: mi.DataclassType,
        NT: mi.NamedTupleType,
        ContractTD: mi.TypedDictType,
        Color: mi.EnumType,
    }


def test_private_get_class_name_contract() -> None:
    assert js._get_class_name(Data) == "Data"
    assert js._get_class_name(G[int]) == "G[int]"
    assert js._get_class_name(StG[Data]) == "StG[Data]"


def test_private_schema_generator_contract() -> None:
    info = mi.type_info(ContractInner)
    generator = js._SchemaGenerator({ContractInner: "ContractInner"}, None, "#/$defs/{name}")

    assert generator.to_schema(info) == {"$ref": "#/$defs/ContractInner"}
    assert generator.to_schema(info, False) == {
        "title": "ContractInner",
        "type": "object",
        "properties": {"i": {"type": "integer"}},
        "required": ["i"],
    }

    seen: list[mi.Type] = []

    class Recording(js._SchemaGenerator):
        def to_schema(self, t: mi.Type, check_ref: bool = True) -> dict[str, Any]:
            seen.append(t)
            return super().to_schema(t, check_ref)

    Recording({ContractInner: "ContractInner"}, None, "#/$defs/{name}").to_schema(info, False)
    assert seen == [info, mi.IntType()]


def test_helper_follows_library_placeholder() -> None:
    field_definition = FieldDefinition.from_annotation(DataclassPerson)

    schema = get_schema_for_field_definition(field_definition)
    assert schema.title == "DataclassPerson"
    assert schema.properties is not None
    assert set(schema.properties) == {"first_name", "last_name", "id", "optional", "complex", "pets"}

    result, schemas = get_components_for_field_definition(field_definition)
    assert isinstance(result, Reference)
    assert result.ref == f"{PREFIX}DataclassPerson"
    assert {"DataclassPerson", "DataclassPet"} <= schemas.keys()


class DecLeaf(msgspec.Struct):
    d: decimal.Decimal


class DecOuter(msgspec.Struct):
    leaf: DecLeaf


@dataclasses.dataclass
class DecLeafHolder:
    name: str
    leaf: DecLeaf


class IntLeaf(msgspec.Struct):
    n: int


class IntOuter(msgspec.Struct):
    leaf: IntLeaf


@dataclasses.dataclass
class IntLeafHolder:
    name: str
    leaf: IntLeaf


@dataclasses.dataclass
class DcLeaf:
    n: int


class DcOuter(msgspec.Struct):
    leaf: DcLeaf


class DcLeafHolder(msgspec.Struct):
    name: str
    leaf: DcLeaf


@attrs.define
class AtLeaf:
    n: int


class AtOuter(msgspec.Struct):
    leaf: AtLeaf


class AtLeafHolder(msgspec.Struct):
    name: str
    leaf: AtLeaf


def leaf_routes(leaf: Any, outer: Any) -> list[Any]:
    @post("/outer", sync_to_thread=False, signature_namespace={"outer": outer})
    def outer_route(data: JSONBody[outer]) -> outer:  # pyright: ignore[reportInvalidTypeForm]
        return data

    @post("/leaf", sync_to_thread=False, signature_namespace={"leaf": leaf})
    def leaf_route(data: JSONBody[leaf]) -> leaf:  # pyright: ignore[reportInvalidTypeForm]
        return data

    return [outer_route, leaf_route]


def dto_route(dto: Any, model: Any) -> Any:
    @post("/dto", dto=dto, sync_to_thread=False, signature_namespace={"model": model})
    def handler(data: JSONBody[model]) -> model:  # pyright: ignore[reportInvalidTypeForm]
        return data

    return handler


@pytest.mark.parametrize("order", [pytest.param(1, id="dto-first"), pytest.param(-1, id="dto-last")])
def test_dto_routes_leave_plain_routes_and_their_own_schemas_unchanged(order: int) -> None:
    plain = document(leaf_routes(DecLeaf, DecOuter))
    litestar_leaf = get_schema_for_field_definition(FieldDefinition.from_annotation(DecLeaf), library_models=False)
    routes = [dto_route(DataclassDTO[DecLeafHolder], DecLeafHolder), *leaf_routes(DecLeaf, DecOuter)]

    doc = document(routes[::order])

    dto_body = components(doc)[body_schema(doc, "/dto")["$ref"].removeprefix(PREFIX)]
    assert {path: doc["paths"][path] for path in plain["paths"]} == plain["paths"]
    assert {name: components(doc)[name] for name in components(plain)} == components(plain)
    assert dto_body["properties"]["leaf"] == {"$ref": f"{PREFIX}DecLeaf"}
    assert components(doc)["DecLeaf"] == litestar_leaf.to_schema()


@pytest.mark.parametrize(
    ("dto", "model", "leaf", "outer"),
    [
        (DataclassDTO[IntLeafHolder], IntLeafHolder, IntLeaf, IntOuter),
        (MsgspecDTO[DcLeafHolder], DcLeafHolder, DcLeaf, DcOuter),
        (MsgspecDTO[AtLeafHolder], AtLeafHolder, AtLeaf, AtOuter),
    ],
)
def test_plain_routes_document_a_class_with_one_component_whatever_the_route_order(
    dto: Any, model: Any, leaf: Any, outer: Any
) -> None:
    plain = document(leaf_routes(leaf, outer))
    docs = [
        document([dto_route(dto, model), *leaf_routes(leaf, outer)]),
        document([*leaf_routes(leaf, outer), dto_route(dto, model)]),
    ]

    for doc in docs:
        assert {path: doc["paths"][path] for path in plain["paths"]} == plain["paths"]
        assert {name: components(doc)[name] for name in components(plain)} == components(plain)
        assert not [name for name in components(doc) if name.startswith(f"{leaf.__name__}_")]


def link_chain(length: int) -> Any:
    model: Any = int
    for index in reversed(range(length)):
        model = msgspec.defstruct(f"Link{index}", [("next", cast("Any", Optional[model]), None)])
    return model


def chain_app() -> Litestar:
    return Litestar([body_only(link_chain(100))], openapi_config=OpenAPIConfig(title="t", version="1"))


def test_long_model_chains_are_documented_above_a_low_recursion_limit() -> None:
    app = chain_app()

    with recursion_limit(500):
        doc = app.openapi_schema.to_schema()
        restored = sys.getrecursionlimit()

    assert restored == 500
    assert len(components(doc)) == 100


def test_concurrent_builds_restore_the_recursion_limit() -> None:
    apps = [chain_app() for _ in range(8)]
    barrier = threading.Barrier(len(apps))

    def build(app: Litestar) -> dict[str, Any]:
        barrier.wait()
        return app.openapi_schema.to_schema()

    interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        with recursion_limit(500), ThreadPoolExecutor(len(apps)) as pool:
            docs = list(pool.map(build, apps))
            restored = sys.getrecursionlimit()
    finally:
        sys.setswitchinterval(interval)

    assert restored == 500
    assert [len(components(doc)) for doc in docs] == [100] * len(apps)


KwargTitled = Annotated[int, KwargDefinition(title="A", description="a", examples=[Example(value=1)], ge=1)]
KwargBody = Annotated[str, BodyKwarg(description="b", max_length=3)]
KwargQuery = Annotated[datetime.date, QueryParameter(title="C", examples=[Example(value=datetime.date(2024, 1, 2))])]
KWARG_PROPERTIES = {
    "a": {"type": "integer", "title": "A", "description": "a", "examples": [1]},
    "b": {"type": "string", "description": "b"},
    "c": {"type": "string", "format": "date", "title": "C", "examples": ["2024-01-02"]},
}


@dataclasses.dataclass
class DcKwargs:
    a: KwargTitled
    b: KwargBody
    c: KwargQuery


class StKwargs(msgspec.Struct):
    a: KwargTitled
    b: KwargBody
    c: KwargQuery


class TdKwargs(TypedDict):
    a: KwargTitled
    b: KwargBody
    c: KwargQuery


@attrs.define
class AtKwargs:
    a: KwargTitled
    b: KwargBody
    c: KwargQuery


@pytest.mark.parametrize("model", [DcKwargs, StKwargs, TdKwargs, AtKwargs])
def test_kwarg_definition_documents_title_description_and_examples_but_no_constraints(model: Any) -> None:
    doc = document([body_only(model)], plugins=(AttrsSchemaPlugin(),))

    assert components(doc)[model.__name__]["properties"] == KWARG_PROPERTIES


def test_kwarg_definition_on_a_model_field_describes_the_reference() -> None:
    @dataclasses.dataclass
    class Outer:
        child: Annotated[DcChild, KwargDefinition(description="the child")]

    properties = components(document([body_only(Outer)]))["Outer"]["properties"]

    assert properties == {"child": {"allOf": [{"$ref": f"{PREFIX}DcChild"}], "description": "the child"}}


@dataclasses.dataclass
class Point:
    x: int


class CopyingPlugin(OpenAPISchemaPlugin):
    def __init__(self, copier: Any) -> None:
        self.copier = copier

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is Point

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        reference = DataclassSchemaPlugin().to_openapi_schema(field_definition, schema_creator)
        return Schema(one_of=[self.copier(reference), Schema(type=OpenAPIType.NULL)])


@pytest.mark.parametrize("copier", [copy.copy, copy.deepcopy, dataclasses.replace], ids=["copy", "deepcopy", "replace"])
def test_copied_placeholder_points_at_the_component(copier: Any) -> None:
    @get("/", sync_to_thread=False)
    def handler() -> Point:
        return Point(1)

    app = Litestar([handler], plugins=[CopyingPlugin(copier)])
    doc = app.openapi_schema.to_schema()

    assert response_schema(doc, method="get") == {"oneOf": [{"$ref": f"{PREFIX}Point"}, {"type": "null"}]}
    assert list(components(doc)) == ["Point"]
    assert "litestar-library" not in msgspec.json.encode(doc).decode()
    assert dataclasses.asdict(app.openapi_schema)["components"]["schemas"]["Point"]["title"] == "Point"
    assert msgspec.to_builtins(app.openapi_schema)["components"]["schemas"]["Point"]["title"] == "Point"


def test_generated_example_of_a_type_outside_msgspec_builtins_uses_the_app_serializer() -> None:
    @get("/", sync_to_thread=False)
    def handler(ip: FromQuery[IPv4Address]) -> None:
        return None

    doc = document([handler], create_examples=True)
    (example,) = doc["paths"]["/"]["get"]["parameters"][0]["schema"]["examples"]

    assert str(IPv4Address(example)) == example
