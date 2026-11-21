# pyright: reportUnnecessaryTypeIgnoreComment=false

import copy
import dataclasses
import datetime
import decimal
import enum
import json
import os
import pathlib
import re
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Annotated, Any, Literal, NotRequired, Optional, TypedDict, Union, cast

import msgspec
import pydantic
import pytest

import litestar
from litestar import Litestar, get, post
from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.schema_generation.library import (
    LOCAL_PREFIX,
    MODES,
    LibraryRequest,
    LibraryRun,
    SchemaMode,
)
from litestar._openapi.schema_generation.library import components as library_components
from litestar._openapi.schema_generation.library._msgspec import _MsgspecResolver
from litestar._openapi.schema_generation.library.components import LibraryComponents
from litestar._openapi.schema_generation.library.converter import json_schema_to_spec
from litestar._openapi.schema_generation.library.exceptions import (
    LibrarySchemaError,
    SchemaConversionError,
    SchemaNameConflictError,
    UnresolvedSchemaError,
)
from litestar._openapi.schema_generation.library.graph import NameCandidates, ResolvedSchemas, SchemaKey, schema_node
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar._openapi.schema_generation.schema import SchemaCreator
from litestar.datastructures import ResponseHeader, UploadFile
from litestar.exceptions import ImproperlyConfiguredException, LitestarWarning
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import Example, Reference, Schema
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.params import Body, FromQuery, JSONBody, MultipartBody, QueryParameter
from litestar.plugins import OpenAPISchemaPlugin
from litestar.typing import FieldDefinition
from tests.helpers import PREFIX, body_schema, components, document, normalise_json_schema, response_schema, route


@dataclasses.dataclass
class Marker:
    value: int = 0


@dataclasses.dataclass
class Other:
    name: str = ""


@dataclasses.dataclass
class Foreign:
    name: str = ""


class ExistingThing:
    pass


Resolve = Callable[[Sequence[LibraryRequest], LibraryRun], ResolvedSchemas]


class FakeResolver(_MsgspecResolver):
    name = "fake"

    def __init__(self) -> None:
        self.resolve_with: Resolve = super().resolve

    def resolve(self, requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        return self.resolve_with(requests, run)


class ForeignResolver(FakeResolver):
    name = "foreign"


FAKE = FakeResolver()
FOREIGN = ForeignResolver()


class FakeLibraryPlugin(OpenAPISchemaPlugin):
    def __init__(self) -> None:
        self.references: list[Reference] = []

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation in (Marker, Other)

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        reference = schema_creator.for_library(field_definition, FAKE)
        self.references.append(reference)
        return reference


class ForeignPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is Foreign

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        return schema_creator.for_library(field_definition, FOREIGN)


class FreshTypePlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is ExistingThing

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        return schema_creator.for_library(FieldDefinition.from_annotation(type("Fresh", (), {})), FAKE)


class ExistingPlugin(OpenAPISchemaPlugin):
    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is ExistingThing

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        return schema_creator.create_component_schema(field_definition, required=[], property_fields={})


class CapturingPlugin(OpenAPISchemaPlugin):
    def __init__(self, *types: Any) -> None:
        self.types = types
        self.records: dict[Any, tuple[str, bool]] = {}
        self.prefer_alias: dict[Any, bool] = {}

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation in self.types

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        self.records[field_definition.annotation] = (schema_creator.schema_mode, schema_creator.library_models)
        self.prefer_alias[field_definition.annotation] = schema_creator.prefer_alias
        return Schema(type=OpenAPIType.STRING)


MARKER_DEF: dict[str, Any] = {"type": "object", "properties": {"value": {"type": "integer"}}}
OTHER_DEF: dict[str, Any] = {"type": "object", "properties": {"name": {"type": "string"}}}


def by_name(request: LibraryRequest) -> str:
    return cast("str", request.annotation.__name__)


def fake_key(resolver: str, def_key: str, defs: Mapping[str, Any]) -> SchemaKey:
    for mode, suffix in MODES:
        stem = def_key.removesuffix(suffix)
        if stem != def_key and stem not in defs and all(f"{stem}{other}" in defs for _, other in MODES):
            return SchemaKey(resolver, stem, mode)
    return SchemaKey(resolver, def_key, "validation")


def resolved(
    roots: Mapping[LibraryRequest, str],
    defs: Mapping[str, Any],
    names: Mapping[str, str] | None = None,
    warnings: tuple[str, ...] = (),
) -> ResolvedSchemas:
    resolver = next(iter(roots)).resolver.name
    keys = {def_key: fake_key(resolver, def_key, defs) for def_key in defs}
    targets = {f"{LOCAL_PREFIX}{def_key}": key for def_key, key in keys.items()}
    nodes = {
        key: schema_node(
            defs[def_key], targets, NameCandidates(str(key.identity), str(key.identity), (names or {}).get(def_key))
        )
        for def_key, key in keys.items()
    }
    return ResolvedSchemas({request: keys[key] for request, key in roots.items() if key in keys}, nodes, warnings)


def canned(
    defs: dict[str, Any],
    names: dict[str, str] | None = None,
    root: Callable[[LibraryRequest], str] = by_name,
) -> Resolve:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        return resolved({request: root(request) for request in requests}, copy.deepcopy(defs), names)

    return resolver


def in_rounds(*resolvers: Resolve, calls: list[list[LibraryRequest]] | None = None) -> Resolve:
    seen: list[list[LibraryRequest]] = [] if calls is None else calls

    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        seen.append(list(requests))
        return resolvers[len(seen) - 1](requests, run)

    return resolver


def delegating_other(defs: dict[str, Any], mode: SchemaMode = "validation", target: Any = Other) -> Resolve:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        other = run.embed(run.schema_creator(mode).for_field_definition(FieldDefinition.from_annotation(target)))
        delegated = copy.deepcopy(defs)
        delegated["Marker"]["properties"]["other"] = other
        return resolved({request: by_name(request) for request in requests}, delegated)

    return resolver


def use(monkeypatch: pytest.MonkeyPatch, resolver: Resolve) -> None:
    monkeypatch.setattr(FAKE, "resolve_with", resolver)
    monkeypatch.setattr(FOREIGN, "resolve_with", resolver)


@pytest.fixture()
def canned_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, canned({"Marker": MARKER_DEF}))


def get_marker() -> Any:
    @get("/", sync_to_thread=False)
    def handler() -> Marker:
        return Marker()

    return handler


def keyed(key: str, annotation: Any = Marker) -> Any:
    return Annotated[annotation, Body(schema_component_key=key)]


def fake_document(handlers: list[Any], plugins: Sequence[Any] = (), **config: Any) -> dict[str, Any]:
    return document(handlers, [FakeLibraryPlugin(), *plugins], **config)


class Colour(enum.Enum):
    RED = "red"
    BLUE = "blue"


class MsgspecModel(msgspec.Struct, tag=True):
    """doc"""

    a: Annotated[int, msgspec.Meta(gt=0, le=10, multiple_of=2, description="d", title="T", examples=[2])] = 1
    s: Annotated[str, msgspec.Meta(min_length=1, max_length=3, pattern="^a")] = "a"
    items_: Annotated[list[int], msgspec.Meta(min_length=1, max_length=4)] = []
    st: set[int] = set()
    tup: tuple[int, str] = (1, "a")
    var: tuple[int, ...] = ()
    d: Annotated[dict[str, int], msgspec.Meta(min_length=1)] = {}
    o: Optional["MsgspecModel"] = None
    u: Union[int, str] = 1
    lit: Literal["a", "b"] = "a"
    colour: Colour = Colour.RED
    b: bytes = b""
    dec: decimal.Decimal = decimal.Decimal(0)
    dt: Optional[datetime.datetime] = None
    tm: Optional[datetime.time] = None
    td: Optional[datetime.timedelta] = None
    uid: Optional[uuid.UUID] = None
    any_: Any = None
    f: Annotated[float, msgspec.Meta(ge=0.0, lt=1.0)] = 0.0
    ex: Annotated[int, msgspec.Meta(extra_json_schema={"deprecated": True, "readOnly": True})] = 0


class TaggedA(msgspec.Struct, tag="a"):
    x: int


class TaggedB(msgspec.Struct, tag="b"):
    y: str


class Mapping_(TypedDict):
    q: int
    r: NotRequired[str]


@dataclasses.dataclass
class Holder:
    u: Union[TaggedA, TaggedB]
    td: Optional[Mapping_] = None


LIBRARY_DEFS = msgspec.json.schema_components([MsgspecModel, Holder], ref_template="#/$defs/{name}")[1]


@pytest.mark.parametrize("name", sorted(LIBRARY_DEFS))
def test_converter_round_trips_library_output(name: str) -> None:
    definition = LIBRARY_DEFS[name]
    dropped: set[str] = set()
    assert json_schema_to_spec(definition, lookup_ref=Reference, dropped=dropped).to_schema() == (
        normalise_json_schema(definition)
    )
    assert not dropped


def test_converter_maps_refs_boolean_schemas_formats_and_discriminators() -> None:
    target = Reference("#/components/schemas/X")
    assert json_schema_to_spec({"$ref": "#/$defs/X"}, lookup_ref=lambda ref: target) is target

    assert json_schema_to_spec({"$ref": "#/$defs/X", "description": "d"}, lookup_ref=Reference).to_schema() == {
        "allOf": [{"$ref": "#/$defs/X"}],
        "description": "d",
    }
    with_all_of = json_schema_to_spec({"$ref": "#/$defs/X", "allOf": [{"type": "object"}]}, lookup_ref=Reference)
    assert with_all_of.to_schema() == {"allOf": [{"$ref": "#/$defs/X"}, {"type": "object"}]}

    inline = Schema(type=OpenAPIType.STRING, description="inline")

    def resolve_inline(ref: str) -> Schema | Reference:
        return inline

    merged = json_schema_to_spec({"$ref": "litestar-embed:0", "title": "T", "default": "a"}, resolve_inline)
    assert merged.to_schema() == {"type": "string", "description": "inline", "title": "T", "default": "a"}
    assert inline.title is None
    for siblings in ({"description": "d"}, {"maxLength": 1}):
        kept = json_schema_to_spec({"$ref": "litestar-embed:0", **siblings}, resolve_inline)
        assert kept.to_schema() == {"allOf": [inline.to_schema()], **siblings}

    closed = json_schema_to_spec({"type": "object", "additionalProperties": False}, lookup_ref=Reference)
    assert isinstance(closed, Schema)
    assert closed.additional_properties is False

    assert json_schema_to_spec({"type": "array", "items": False}, lookup_ref=Reference).to_schema() == {
        "type": "array",
        "items": {"not": {}},
    }
    loose_tuple = {"type": "array", "prefixItems": [{"type": "integer"}], "items": False}
    assert json_schema_to_spec(loose_tuple, lookup_ref=Reference).to_schema() == {
        "type": "array",
        "prefixItems": [{"type": "integer"}],
        "items": {"not": {}},
    }
    assert json_schema_to_spec(True, lookup_ref=Reference).to_schema() == {}
    assert json_schema_to_spec(False, lookup_ref=Reference).to_schema() == {"not": {}}

    nullable = json_schema_to_spec({"type": ["string", "null"]}, lookup_ref=Reference)
    assert isinstance(nullable, Schema)
    assert nullable.type == [OpenAPIType.STRING, OpenAPIType.NULL]

    decimal_schema = json_schema_to_spec({"type": "string", "format": "decimal"}, lookup_ref=Reference)
    uuid_schema = json_schema_to_spec({"type": "string", "format": "uuid"}, lookup_ref=Reference)
    assert isinstance(decimal_schema, Schema)
    assert isinstance(uuid_schema, Schema)
    decimal_format: object = decimal_schema.format
    assert decimal_format == "decimal"
    assert not isinstance(decimal_format, OpenAPIFormat)
    assert uuid_schema.format is OpenAPIFormat.UUID

    discriminated = json_schema_to_spec(
        {"oneOf": [{"$ref": "#/$defs/A"}], "discriminator": {"propertyName": "kind", "mapping": {"a": "#/$defs/A"}}},
        lookup_ref=lambda ref: Reference(ref.replace("#/$defs/", PREFIX)),
    )
    assert discriminated.to_schema() == {
        "oneOf": [{"$ref": f"{PREFIX}A"}],
        "discriminator": {"propertyName": "kind", "mapping": {"a": f"{PREFIX}A"}},
    }

    def inline_a(ref: str) -> Schema | Reference:
        return Schema() if ref == "#/$defs/A" else Reference(ref.replace("#/$defs/", PREFIX))

    partly_inline = {"propertyName": "kind", "mapping": {"a": "#/$defs/A", "b": "#/$defs/B"}}
    assert json_schema_to_spec({"discriminator": partly_inline}, lookup_ref=inline_a).to_schema() == {
        "discriminator": {"propertyName": "kind", "mapping": {"b": f"{PREFIX}B"}}
    }
    only_inline = {"propertyName": "kind", "mapping": {"a": "#/$defs/A"}}
    assert json_schema_to_spec({"discriminator": only_inline}, lookup_ref=inline_a).to_schema() == {
        "discriminator": {"propertyName": "kind"}
    }

    with pytest.raises(ImproperlyConfiguredException, match="str"):
        json_schema_to_spec({"type": "str"}, lookup_ref=Reference)


@pytest.mark.parametrize(
    ("value", "key", "expected"),
    [
        ({"$defs": {}}, "$defs", {}),
        ({"$schema": "https://json-schema.org/draft/2020-12/schema"}, "$schema", {}),
        ({"x-internal": True, "type": "integer"}, "x-internal", {"type": "integer"}),
        ({"externalDocs": {"url": "https://example.org"}}, "externalDocs", {}),
        ({"unknownKeyword": 1}, "unknownKeyword", {}),
        (
            {"type": "object", "properties": {"a": {"unknownKeyword": 1}}},
            "unknownKeyword",
            {"type": "object", "properties": {"a": {}}},
        ),
    ],
)
def test_converter_drops_unknown_keys(value: dict[str, Any], key: str, expected: dict[str, Any]) -> None:
    dropped: set[str] = set()
    assert json_schema_to_spec(value, lookup_ref=Reference, dropped=dropped).to_schema() == expected
    assert dropped == {key}


class ExtraKeysStruct(msgspec.Struct):
    a: Annotated[int, msgspec.Meta(extra_json_schema={"x-order": 1})]
    b: Annotated[int, msgspec.Meta(extra_json_schema={"x-order": 2, "$comment": "c"})]


@dataclasses.dataclass
class ExtraKeysDataclass:
    a: Annotated[int, msgspec.Meta(extra_json_schema={"nullable": True})]


@pytest.mark.parametrize(
    ("model", "keys"),
    [
        (ExtraKeysStruct, ["$comment", "x-order"]),
        (ExtraKeysDataclass, ["nullable"]),
    ],
)
def test_unsupported_keys_are_dropped_with_one_warning_per_model_and_key(model: Any, keys: list[str]) -> None:
    def handler(data: Any) -> Any:
        return data

    handler.__annotations__ = {"data": JSONBody[model], "return": model}  # type: ignore[misc]
    app = Litestar([post("/", sync_to_thread=False)(handler)])

    with pytest.warns(LitestarWarning) as record:
        doc = app.openapi_schema.to_schema()

    assert sorted(str(warning.message) for warning in record) == [
        f"The JSON schema key {key!r} of {model.__name__!r} cannot be represented in the OpenAPI document "
        "and is dropped"
        for key in keys
    ]
    assert not [key for key in keys if key in json.dumps(doc)]


@pytest.mark.usefixtures("canned_marker")
@pytest.mark.parametrize(
    ("generate_examples", "examples", "generated"),
    [(True, None, True), (False, None, False), (True, [Example(value={"value": 1})], False)],
)
def test_response_spec_generates_examples_unless_disabled_or_given(
    generate_examples: bool, examples: Optional[list[Example]], generated: bool
) -> None:
    @get(
        "/",
        responses={
            404: ResponseSpec(
                data_container=Marker, description="d", generate_examples=generate_examples, examples=examples
            )
        },
    )
    def handler() -> None:
        return None

    schema = response_schema(fake_document([handler]), method="get", status="404")

    assert ("examples" in schema) is generated


def captured_requests(creator: SchemaCreator, monkeypatch: pytest.MonkeyPatch) -> list[LibraryRequest]:
    requests: list[LibraryRequest] = []

    def resolver(received: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        requests.extend(received)
        return resolved(dict.fromkeys(received, "X"), {"X": {}})

    use(monkeypatch, resolver)
    context = OpenAPIContext(openapi_config=OpenAPIConfig(title="t", version="1"), plugins=[])
    creator.schema_registry.library.resolve(context)
    return requests


def test_for_library_records_request_and_returns_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    creator = SchemaCreator(schema_mode="serialization")
    field_definition = FieldDefinition.from_annotation(Marker)

    first = creator.for_library(field_definition, FAKE)
    second = creator.for_library(field_definition, FAKE)

    components = creator.schema_registry.library
    assert first is not second
    assert components.is_placeholder(first)
    assert components.is_placeholder(second)
    assert creator.schema_registry.component_for(first) is None
    with pytest.raises(ImproperlyConfiguredException, match=r"component_for"):
        creator.schema_registry.from_reference(first)
    assert captured_requests(creator, monkeypatch) == [LibraryRequest(Marker, FAKE, "serialization")]

    existing = FieldDefinition.from_annotation(ExistingThing)
    creator.schema_registry.get_schema_for_field_definition(existing)
    existing_reference = creator.schema_registry.get_reference_for_field_definition(existing)
    assert existing_reference is not None
    assert not components.is_placeholder(existing_reference)


MARKER_IN, MARKER_OUT = LibraryRequest(Marker, FAKE, "validation"), LibraryRequest(Marker, FAKE, "serialization")
OTHER_IN = LibraryRequest(Other, FAKE, "validation")
CHANGED_DEF: dict[str, Any] = {"type": "object", "properties": {"changed": {"type": "boolean"}}}


@pytest.mark.parametrize(
    ("handler", "rounds", "expected_calls"),
    [
        pytest.param(
            get_marker(),
            [delegating_other({"Marker": MARKER_DEF}), delegating_other({"Marker": CHANGED_DEF, "Other": OTHER_DEF})],
            [[MARKER_OUT], [MARKER_OUT, OTHER_IN]],
            id="one-mode",
        ),
        pytest.param(
            route(JSONBody[Marker], Marker),
            [delegating_other({"Marker": MARKER_DEF}), delegating_other({"Marker": CHANGED_DEF, "Other": OTHER_DEF})],
            [[MARKER_IN, MARKER_OUT], [MARKER_IN, MARKER_OUT, OTHER_IN]],
            id="both-modes",
        ),
    ],
)
def test_resolve_rounds_pass_all_requests_and_keep_the_latest_result(
    handler: Any, rounds: list[Resolve], expected_calls: list[list[LibraryRequest]], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[LibraryRequest]] = []
    use(monkeypatch, in_rounds(*rounds, calls=calls))

    schemas = components(fake_document([handler]))

    assert calls == expected_calls
    assert schemas == {
        "Marker": {
            "type": "object",
            "properties": {"changed": {"type": "boolean"}, "other": {"$ref": f"{PREFIX}Other"}},
        },
        "Other": OTHER_DEF,
    }


def use_two_rounds(monkeypatch: pytest.MonkeyPatch, cap: int) -> None:
    monkeypatch.setattr(library_components, "_MAX_ROUNDS", cap)
    use(
        monkeypatch,
        in_rounds(
            delegating_other({"Marker": MARKER_DEF}),
            delegating_other({"Marker": CHANGED_DEF, "Other": OTHER_DEF}),
        ),
    )


def test_resolution_needing_exactly_the_round_cap_settles(monkeypatch: pytest.MonkeyPatch) -> None:
    use_two_rounds(monkeypatch, cap=2)

    assert set(components(fake_document([get_marker()]))) == {"Marker", "Other"}


@pytest.mark.parametrize(("mode", "prefer_alias"), [("validation", True), ("serialization", False)])
def test_types_handed_back_to_litestar_are_documented_in_the_mode_without_examples(
    mode: SchemaMode, prefer_alias: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = CapturingPlugin(ExistingThing)

    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        creator = run.schema_creator(mode)
        properties = {
            name: run.embed(creator.for_field_definition(FieldDefinition.from_annotation(annotation)))
            for name, annotation in (("other", Other), ("existing", ExistingThing))
        }
        return resolved(
            {request: by_name(request) for request in requests},
            {"Marker": {"type": "object", "properties": properties}, "Other": OTHER_DEF},
        )

    use(monkeypatch, resolver)

    schemas = components(fake_document([get_marker()], plugins=[plugin], create_examples=True))

    assert schemas["Marker"]["properties"] == {"other": {"$ref": f"{PREFIX}Other"}, "existing": {"type": "string"}}
    assert plugin.records == {ExistingThing: (mode, True)}
    assert plugin.prefer_alias == {ExistingThing: prefer_alias}


BLOCKED_PYDANTIC_APP = """
import dataclasses
import sys
from importlib.abc import MetaPathFinder

import msgspec


class BlockPydantic(MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name.split(".")[0] in {"pydantic", "pydantic_core"}:
            raise ImportError(name)


sys.meta_path.insert(0, BlockPydantic())

from litestar import Litestar, post
from litestar.openapi.config import OpenAPIConfig
from litestar.params import JSONBody


@dataclasses.dataclass
class Item:
    value: int


class Box(msgspec.Struct):
    item: Item


@post("/", sync_to_thread=False)
def handler(data: JSONBody[Item]) -> Box:
    return Box(item=data)


app = Litestar([handler], openapi_config=OpenAPIConfig(title="t", version="1", create_examples=True))
operation = app.openapi_schema.to_schema()["paths"]["/"]["post"]
assert operation["requestBody"]["content"]["application/json"]["schema"]["examples"]
assert operation["responses"]["201"]["content"]["application/json"]["schema"]["examples"]
assert not [module for module in sys.modules if module.split(".")[0] in {"pydantic", "pydantic_core"}]
"""


def test_library_schemas_and_examples_without_pydantic() -> None:
    root = pathlib.Path(litestar.__file__).parent.parent
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(root), os.environ.get("PYTHONPATH")]))}

    result = subprocess.run([sys.executable, "-c", BLOCKED_PYDANTIC_APP], env=env, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_same_base_name_in_another_library_gets_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    def library(root: str, scalar: str, ref: str = "#/$defs/", suffix: str = "") -> dict[str, Any]:
        return {
            root: {
                "type": "object",
                "properties": {"s": {"$ref": f"{ref}Shared{suffix}"}, "a": {"$ref": f"{ref}Address{suffix}"}},
            },
            f"Shared{suffix}": {"type": scalar},
            f"Address{suffix}": {"type": "object", "properties": {"city": {"$ref": f"{ref}City{suffix}"}}},
            f"City{suffix}": {"type": scalar},
        }

    use(
        monkeypatch,
        in_rounds(delegating_other(library("Marker", "string"), target=Foreign), canned(library("Foreign", "integer"))),
    )

    schemas = components(fake_document([get_marker()], plugins=[ForeignPlugin()]))

    expected = {**library("Marker", "string", PREFIX), **library("Foreign", "integer", PREFIX, "_2")}
    expected["Marker"]["properties"]["other"] = {"$ref": f"{PREFIX}Foreign"}
    assert schemas == expected


def by_mode(request: LibraryRequest) -> str:
    return "Marker-Input" if request.mode == "validation" else "Marker-Output"


INNER_ROOT: dict[str, Any] = {"type": "object", "properties": {"s": {"$ref": "#/$defs/Inner"}}}


@pytest.mark.parametrize(
    ("resolver", "response", "expected", "refs"),
    [
        pytest.param(
            canned({"Marker": MARKER_DEF}),
            Marker,
            {"Custom": MARKER_DEF, "Marker": MARKER_DEF},
            ("Custom", "Marker"),
            id="copy-of-root",
        ),
        pytest.param(
            canned({"Marker-Input": MARKER_DEF, "Marker-Output": OTHER_DEF}, root=by_mode),
            keyed("Custom"),
            {"Custom-Input": MARKER_DEF, "Custom-Output": OTHER_DEF},
            ("Custom-Input", "Custom-Output"),
            id="both-directions-keep-suffixes",
        ),
        pytest.param(
            canned({"Marker": MARKER_DEF}, names={"Marker": "Custom"}),
            Marker,
            {"Custom": MARKER_DEF},
            ("Custom", "Custom"),
            id="shared-with-result-name",
        ),
        pytest.param(
            canned({"Marker": INNER_ROOT, "Other": INNER_ROOT, "Inner": {"type": "string"}}),
            keyed("Custom", Other),
            {
                "Custom": {"type": "object", "properties": {"s": {"$ref": f"{PREFIX}Inner"}}},
                "Inner": {"type": "string"},
            },
            ("Custom", "Custom"),
            id="same-key-identical-schema",
        ),
        pytest.param(canned({"Marker": MARKER_DEF}), None, {"Custom": MARKER_DEF}, ("Custom",), id="alone"),
        pytest.param(
            canned({"Marker-Input": MARKER_DEF}, root=lambda request: "Marker-Input"),
            None,
            {"Custom": MARKER_DEF},
            ("Custom",),
            id="alone-drops-suffix",
        ),
    ],
)
def test_named_request_components(
    resolver: Resolve,
    response: Any,
    expected: dict[str, Any],
    refs: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use(monkeypatch, resolver)

    doc = fake_document([route(keyed("Custom"), response)])
    schemas = [body_schema(doc), *([] if response is None else [response_schema(doc)])]

    assert components(doc) == expected
    assert schemas == [{"$ref": f"{PREFIX}{ref}"} for ref in refs]


def test_explicit_name_wins_over_an_earlier_automatic_name(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        named_other = FieldDefinition.from_annotation(Other, kwarg_definition=Body(schema_component_key="Foo"))
        foo = copy.deepcopy(MARKER_DEF)
        foo["properties"]["other"] = run.embed(run.schema_creator("validation").for_field_definition(named_other))
        return resolved(
            {request: "Foo" if request.annotation is Marker else "Other" for request in requests},
            {"Foo": foo, "Other": OTHER_DEF},
        )

    use(monkeypatch, resolver)

    schemas = components(fake_document([get_marker()]))

    assert sorted(schemas) == ["Foo", "Foo_2"]
    assert schemas["Foo"] == OTHER_DEF
    assert schemas["Foo_2"]["properties"]["other"] == {"$ref": f"{PREFIX}Foo"}


def test_existing_component_keeps_name_over_library_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, canned({"ExistingThing": MARKER_DEF}, root=lambda request: "ExistingThing"))

    @get("/library")
    def library_handler() -> Marker:
        return Marker()

    @get("/existing")
    def existing_handler() -> ExistingThing:
        return ExistingThing()

    doc = fake_document([library_handler, existing_handler], plugins=[ExistingPlugin()])

    assert components(doc)["ExistingThing"]["title"] == "ExistingThing"
    assert components(doc)["ExistingThing_2"] == MARKER_DEF
    assert response_schema(doc, "/library", method="get") == {"$ref": f"{PREFIX}ExistingThing_2"}
    assert response_schema(doc, "/existing", method="get") == {"$ref": f"{PREFIX}ExistingThing"}


class Opaque:
    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return self.value


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (decimal.Decimal("1.5"), "1.5"),
        (b"YQ==", "YQ=="),
        (b"a", "YQ=="),
        (float("nan"), None),
        (float("inf"), "inf"),
        (1, 1.0),
        (1, True),
        ((1, 2), [1, 2]),
        ({1: "a"}, {"1": "a"}),
        (frozenset({"a"}), ["a"]),
        (Opaque("x"), "x"),
        (Opaque("['object', 'x']"), ["object", "x"]),
    ],
)
def test_different_embedded_values_never_share_a_token(
    first: Any, second: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    tokens: list[dict[str, str]] = []

    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        for value in (first, second, first):
            tokens.append(run.embed(Schema(default=value)))
        return resolved(dict.fromkeys(requests, "Marker"), {"Marker": MARKER_DEF})

    use(monkeypatch, resolver)
    fake_document([get_marker()])

    assert tokens[0] == tokens[2] != tokens[1]


def test_embedded_existing_reference_gets_final_path(monkeypatch: pytest.MonkeyPatch) -> None:
    tokens: list[dict[str, str]] = []

    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        creator = run.schema_creator("serialization")
        for _ in range(2):
            tokens.append(run.embed(creator.for_field_definition(FieldDefinition.from_annotation(ExistingThing))))
        return resolved(
            dict.fromkeys(requests, "Marker"), {"Marker": {"type": "object", "properties": {"existing": tokens[0]}}}
        )

    use(monkeypatch, resolver)

    doc = fake_document([get_marker()], plugins=[ExistingPlugin()])

    assert tokens[0] == tokens[1]
    assert components(doc)["Marker"]["properties"]["existing"] == {"$ref": f"{PREFIX}ExistingThing"}
    assert "ExistingThing" in components(doc)


NULL = {"type": "null"}
MIN_ONE = Schema(min_length=1)
CONDITIONAL_SCALARS = {
    "not": Schema(type=OpenAPIType.STRING, schema_not=MIN_ONE),
    "if": Schema(type=OpenAPIType.STRING, schema_if=MIN_ONE),
    "then": Schema(type=OpenAPIType.STRING, then=MIN_ONE),
    "else": Schema(type=OpenAPIType.STRING, schema_else=MIN_ONE),
}


def test_nullable_embedded_scalar_is_a_type_array(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        scalar = run.embed(Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.BINARY))
        enum = run.embed(Schema(type=OpenAPIType.STRING, enum=["a"]))
        conditional = {key: {"anyOf": [run.embed(scalar), NULL]} for key, scalar in CONDITIONAL_SCALARS.items()}
        properties = {
            **conditional,
            "scalar": {"anyOf": [scalar, {"type": "null"}], "title": "S"},
            "null_first": {"anyOf": [{"type": "null"}, scalar]},
            "enum": {"anyOf": [enum, {"type": "null"}]},
            "ref": {"anyOf": [{"$ref": "#/$defs/Other"}, {"type": "null"}]},
            "inline": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        }
        return resolved(
            dict.fromkeys(requests, "Marker"),
            {"Marker": {"type": "object", "properties": properties}, "Other": OTHER_DEF},
        )

    use(monkeypatch, resolver)

    nullable_binary = {"type": ["string", "null"], "format": "binary"}
    assert components(fake_document([get_marker()]))["Marker"]["properties"] == {
        **{key: {"anyOf": [{"type": "string", key: {"minLength": 1}}, NULL]} for key in CONDITIONAL_SCALARS},
        "scalar": {**nullable_binary, "title": "S"},
        "null_first": nullable_binary,
        "enum": {"anyOf": [{"type": "string", "enum": ["a"]}, {"type": "null"}]},
        "ref": {"anyOf": [{"$ref": f"{PREFIX}Other"}, {"type": "null"}]},
        "inline": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    }


@dataclasses.dataclass
class DcUploadForm:
    file: UploadFile
    opt: Optional[UploadFile] = None


class StUploadForm(msgspec.Struct):
    file: UploadFile
    opt: Optional[UploadFile] = None


class PydanticUploadForm(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    file: UploadFile
    opt: Optional[UploadFile] = None


@pytest.mark.parametrize("form", [DcUploadForm, StUploadForm, PydanticUploadForm])
def test_optional_upload_file_in_multipart_form_is_a_type_array(form: Any) -> None:
    @post("/", signature_namespace={"form": form})
    async def handler(data: MultipartBody[form]) -> None:  # pyright: ignore[reportInvalidTypeForm]
        return None

    properties = components(fake_document([handler]))[form.__name__]["properties"]

    assert properties["file"] == {"type": "string", "format": "binary", "contentMediaType": "application/octet-stream"}
    assert properties["opt"] == {**properties["file"], "type": ["string", "null"]}


@dataclasses.dataclass
class BodyType:
    pass


@dataclasses.dataclass
class QueryType:
    pass


@dataclasses.dataclass
class ResponseType:
    pass


@dataclasses.dataclass
class AdditionalType:
    pass


@pytest.mark.parametrize("create_examples", [True, False])
def test_schema_mode_per_call_site(create_examples: bool) -> None:
    plugin = CapturingPlugin(BodyType, QueryType, ResponseType, AdditionalType, str)

    @post(
        "/",
        responses={400: ResponseSpec(data_container=AdditionalType)},
        response_headers=[ResponseHeader(name="x", value="1")],
    )
    def handler(data: JSONBody[BodyType], q: FromQuery[QueryType]) -> ResponseType:
        return ResponseType()

    Litestar(
        [handler],
        plugins=[plugin],
        openapi_config=OpenAPIConfig(title="t", version="1", create_examples=create_examples),
    ).openapi_schema.to_schema()

    assert plugin.records == {
        BodyType: ("validation", True),
        QueryType: ("validation", True),
        ResponseType: ("serialization", True),
        AdditionalType: ("serialization", True),
        str: ("serialization", True),
    }


@pytest.mark.usefixtures("canned_marker")
def test_placeholder_wrappers_get_generated_examples() -> None:
    @post("/")
    def required(data: JSONBody[Marker]) -> None:
        return None

    @post("/optional")
    def optional(data: JSONBody[Optional[Marker]] = Marker(value=1)) -> None:
        return None

    doc = fake_document([required, optional], create_examples=True)
    ref = {"$ref": f"{PREFIX}Marker"}

    assert body_schema(doc)["allOf"] == [ref]
    assert body_schema(doc)["examples"]
    assert body_schema(doc, "/optional")["oneOf"] == [ref, NULL]
    assert body_schema(doc, "/optional")["default"] == {"value": 1}
    assert body_schema(doc, "/optional")["examples"]
    assert components(doc) == {"Marker": MARKER_DEF}


def test_replace_and_not_generating_examples_keep_mode_and_switch() -> None:
    creator = SchemaCreator(generate_examples=True, schema_mode="serialization", library_models=False)

    without_examples = creator.not_generating_examples
    assert without_examples.generate_examples is False
    assert without_examples.prefer_alias is False
    assert without_examples.schema_mode == "serialization"
    assert without_examples.library_models is False
    assert without_examples.schema_registry is creator.schema_registry

    assert without_examples.not_generating_examples is without_examples

    switched = creator.replace(library_models=True)
    assert switched.library_models is True
    assert switched.schema_registry is creator.schema_registry
    assert all(
        getattr(switched, slot) == getattr(creator, slot)
        for slot in SchemaCreator.__slots__
        if slot != "library_models"
    )


@pytest.mark.usefixtures("canned_marker")
def test_placeholder_use_site_metadata_stays_on_the_wrapper() -> None:
    @post("/")
    def described(
        data: Annotated[Marker, Body(description="d", schema_extra={"deprecated": True})],
    ) -> Optional[Marker]:
        return None

    @post("/default")
    def with_default(data: JSONBody[Marker] = Marker(value=3)) -> None:
        return None

    @post("/const")
    def with_const(data: Annotated[Marker, Body(const=True)] = Marker(value=1)) -> None:
        return None

    @post("/plain")
    def plain(data: JSONBody[Marker]) -> Marker:
        return data

    @get("/query-described")
    def query_described(m: Annotated[Marker, QueryParameter(description="q")]) -> None:
        return None

    @get("/query-titled")
    def query_titled(m: Annotated[Marker, QueryParameter(title="t")]) -> None:
        return None

    @get("/query-plain")
    def query_plain(m: FromQuery[Marker]) -> None:
        return None

    @get("/encoded", content_encoding="base64", content_media_type="image/png")
    def encoded() -> Marker:
        return Marker()

    doc = fake_document(
        [described, with_default, with_const, plain, query_described, query_titled, query_plain, encoded]
    )
    ref = {"$ref": f"{PREFIX}Marker"}
    described_param, titled_param, plain_param = (
        doc["paths"][f"/query-{name}"]["get"]["parameters"][0] for name in ("described", "titled", "plain")
    )

    assert body_schema(doc) == {"allOf": [ref], "description": "d", "deprecated": True}
    assert response_schema(doc) == {"oneOf": [ref, NULL]}
    assert body_schema(doc, "/default") == {"allOf": [ref], "default": {"value": 3}}
    assert body_schema(doc, "/const") == {"allOf": [ref], "const": {"value": 1}, "default": {"value": 1}}
    assert body_schema(doc, "/plain") == response_schema(doc, "/plain") == ref
    assert described_param["description"] == "q"
    assert described_param["schema"] == {"allOf": [ref], "description": "q"}
    assert "description" not in titled_param
    assert titled_param["schema"] == {"allOf": [ref], "title": "t"}
    assert "description" not in plain_param
    assert plain_param["schema"] == ref
    assert response_schema(doc, "/encoded", method="get") == {
        "allOf": [ref],
        "contentEncoding": "base64",
        "contentMediaType": "image/png",
    }
    assert components(doc) == {"Marker": MARKER_DEF}


class Unclaimed:
    pass


class CountingPlugin(OpenAPISchemaPlugin):
    def __init__(self, error: bool) -> None:
        self.error = error
        self.calls = 0

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation is Unclaimed

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema:
        self.calls += 1
        if self.error:
            raise RuntimeError("boom")
        return Schema(type=OpenAPIType.STRING)


def test_input_example_without_a_claiming_resolver_uses_the_app_serializer() -> None:
    creator = SchemaCreator(plugins=[], type_encoders={Unclaimed: lambda _: "encoded"})

    for _ in range(2):
        assert creator.schema_registry.library.to_input_example(creator, Unclaimed()) == "encoded"


def test_input_example_the_app_serializer_cannot_encode_raises_type_error() -> None:
    creator = SchemaCreator(plugins=[])

    with pytest.raises(TypeError, match="Unsupported type"):
        creator.schema_registry.library.to_input_example(creator, Unclaimed())


@pytest.mark.parametrize("error", [False, True])
def test_input_example_of_a_plugin_claimed_type_asks_the_plugin_once(error: bool) -> None:
    plugin = CountingPlugin(error=error)
    creator = SchemaCreator(plugins=[plugin])

    for _ in range(2):
        with pytest.raises(TypeError, match="Unsupported type"):
            creator.schema_registry.library.to_input_example(creator, Unclaimed())

    assert plugin.calls == 1


def raise_never_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    creator = SchemaCreator(plugins=openapi_schema_plugins)
    creator.for_field_definition(FieldDefinition.from_annotation(Marker))
    creator.schema_registry.generate_components_schemas()


def raise_unsettled(monkeypatch: pytest.MonkeyPatch) -> None:
    use_two_rounds(monkeypatch, cap=1)
    fake_document([get_marker()])


def raise_never_settled(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        fresh = run.embed(
            run.schema_creator("validation").for_field_definition(FieldDefinition.from_annotation(ExistingThing))
        )
        return resolved(dict.fromkeys(requests, "Def"), {"Def": {"type": "object", "properties": {"x": fresh}}})

    use(monkeypatch, resolver)
    fake_document([get_marker()], plugins=[FreshTypePlugin()])


def raise_recursion(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        raise RecursionError

    use(monkeypatch, resolver)
    fake_document([get_marker()])


def raise_name_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, canned({"Marker": MARKER_DEF, "Other": OTHER_DEF}))
    fake_document([route(keyed("K"), keyed("K", Other))])


def referencing(ref: str) -> Resolve:
    return canned({"Marker": {"type": "object", "properties": {"m": {"$ref": ref}}}})


def raise_unresolvable_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, referencing("#/$defs/Missing"))
    fake_document([get_marker()])


def raise_external_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, referencing("https://example.org/schema"))
    fake_document([get_marker()])


def raise_bare_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, canned({"Marker": {"$ref": "#/$defs/Other"}, "Other": OTHER_DEF}))
    fake_document([get_marker()])


def raise_undocumentable(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, canned({}, root=lambda request: "Missing"))
    fake_document([get_marker()])


@pytest.mark.parametrize(
    ("trigger", "error", "message"),
    [
        pytest.param(
            raise_never_resolved,
            UnresolvedSchemaError,
            r"The library-generated schemas of \[<class '.*Marker'>\] were never resolved; a SchemaCreator documents "
            r"them only within the OpenAPI document of an application",
            id="never-resolved",
        ),
        pytest.param(
            raise_unsettled,
            UnresolvedSchemaError,
            r"Library-generated schemas did not settle after 1 resolution rounds: every round gave the fake schema "
            r"resolver new types to document, most recently \[<class '.*Other'>\]",
            id="unsettled",
        ),
        pytest.param(
            raise_never_settled,
            UnresolvedSchemaError,
            r"Library-generated schemas did not settle after 1000 resolution rounds: every round gave the fake schema "
            r"resolver new types to document, most recently \[<class '.*Fresh'>\]",
            id="never-settles",
        ),
        pytest.param(
            raise_recursion,
            UnresolvedSchemaError,
            r"The fake schema resolver exceeded the maximum recursion depth",
            id="recursion-limit",
        ),
        pytest.param(
            raise_name_conflict,
            SchemaNameConflictError,
            r"Schema component keys must be unique\. Cannot use the key 'K' for a library-generated schema, it is "
            r"already used by a different schema",
            id="explicit-name-taken",
        ),
        pytest.param(
            raise_unresolvable_ref,
            SchemaConversionError,
            r"Cannot resolve '#/\$defs/Missing' in a library-generated schema",
            id="unresolvable-reference",
        ),
        pytest.param(
            raise_external_ref,
            SchemaConversionError,
            r"Cannot resolve 'https://example\.org/schema' in a library-generated schema",
            id="external-reference",
        ),
        pytest.param(
            raise_bare_reference,
            SchemaConversionError,
            r"The library-generated schema 'Marker' is a bare reference",
            id="bare-reference",
        ),
        pytest.param(
            raise_undocumentable,
            SchemaConversionError,
            r"The fake schema resolver cannot document <class '.*Marker'> as a component",
            id="cannot-document",
        ),
    ],
)
def test_library_errors_are_typed(
    trigger: Callable[[pytest.MonkeyPatch], None],
    error: type[LibrarySchemaError],
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        trigger(monkeypatch)

    assert type(exc_info.value) is error
    assert isinstance(exc_info.value, LibrarySchemaError)
    assert re.fullmatch(message, exc_info.value.detail)
    assert str(exc_info.value) == f"500: {exc_info.value.detail}"


def resolved_library(monkeypatch: pytest.MonkeyPatch, resolver: Resolve) -> tuple[LibraryComponents, Reference]:
    use(monkeypatch, resolver)
    creator = SchemaCreator()
    placeholder = creator.for_library(FieldDefinition.from_annotation(Marker), FAKE)
    creator.schema_registry.library.resolve(
        OpenAPIContext(openapi_config=OpenAPIConfig(title="t", version="1"), plugins=[])
    )
    return creator.schema_registry.library, placeholder


def test_freeze_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        return resolved(dict.fromkeys(requests, "Marker"), {"Marker": MARKER_DEF}, warnings=("w",))

    library, _ = resolved_library(monkeypatch, resolver)

    with pytest.warns(LitestarWarning) as record:
        first = library.freeze({})
        second = library.freeze({})

    assert second is first
    assert [str(warning.message) for warning in record] == ["w"]
    assert {name: schema.to_schema() for name, schema in first.components.items()} == {"Marker": MARKER_DEF}
    assert first.targets == {f"{library_components._PLACEHOLDER_PREFIX}0": f"{PREFIX}Marker"}
    assert isinstance(first.components, MappingProxyType)
    assert isinstance(first.targets, MappingProxyType)


def test_placeholder_after_freeze_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    library, _ = resolved_library(monkeypatch, canned({"Marker": MARKER_DEF}))
    library.freeze({})

    with pytest.raises(LibrarySchemaError) as exc_info:
        library.placeholder(FieldDefinition.from_annotation(Other), FAKE, "validation")

    assert exc_info.value.detail == (
        "Cannot request a library-generated schema once the components of the document are generated"
    )


def test_point_references_before_freeze_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    library, placeholder = resolved_library(monkeypatch, canned({"Marker": MARKER_DEF}))
    token = placeholder.ref

    library.point_references(placeholder)
    assert placeholder.ref == token

    library.freeze({})
    library.point_references(placeholder)
    assert placeholder.ref == f"{PREFIX}Marker"


def test_two_resolvers_of_one_name_raise() -> None:
    library = LibraryComponents()
    library.placeholder(FieldDefinition.from_annotation(Marker), FAKE, "validation")

    with pytest.raises(LibrarySchemaError, match="Two schema resolvers are named 'fake'"):
        library.placeholder(FieldDefinition.from_annotation(Other), FakeResolver(), "validation")


def test_a_schema_for_a_request_the_resolver_was_not_given_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        extra = LibraryRequest(Other, FAKE, "validation")
        return resolved({**dict.fromkeys(requests, "Marker"), extra: "Marker"}, {"Marker": MARKER_DEF})

    with pytest.raises(LibrarySchemaError, match="returned schemas for requests it was not given"):
        resolved_library(monkeypatch, resolver)


def test_a_schema_keyed_for_another_resolver_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        key = SchemaKey("elsewhere", "Marker", "validation")
        node = schema_node(MARKER_DEF, {}, NameCandidates("Marker", "Marker"))
        return ResolvedSchemas(dict.fromkeys(requests, key), {key: node})

    with pytest.raises(LibrarySchemaError, match="keyed for another resolver"):
        resolved_library(monkeypatch, resolver)


def test_unknown_json_schema_type_raises_a_conversion_error() -> None:
    with pytest.raises(SchemaConversionError, match="Unsupported JSON schema type 'money'"):
        json_schema_to_spec({"type": "money"}, lambda ref: Reference(ref), set())
