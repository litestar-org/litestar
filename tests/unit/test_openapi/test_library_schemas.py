# pyright: reportUnnecessaryTypeIgnoreComment=false

import copy
import dataclasses
import datetime
import decimal
import enum
import json
import os
import pathlib
import subprocess
import sys
import uuid
from collections.abc import Callable, Sequence
from typing import Annotated, Any, Generic, Literal, NotRequired, Optional, TypedDict, TypeVar, Union, cast

import msgspec
import pytest

import litestar
from litestar import Litestar, get, post
from litestar._openapi.datastructures import OpenAPIContext
from litestar._openapi.plugin import OpenAPIPlugin
from litestar._openapi.schema_generation.library import (
    LibraryRequest,
    LibraryResolver,
    LibraryResult,
    LibraryRun,
    SchemaMode,
    build_result,
    map_references,
    unique_names,
)
from litestar._openapi.schema_generation.library import components as library_components
from litestar._openapi.schema_generation.library._msgspec import MSGSPEC_RESOLVER
from litestar._openapi.schema_generation.library.converter import json_schema_to_spec
from litestar._openapi.schema_generation.plugins import openapi_schema_plugins
from litestar._openapi.schema_generation.schema import SchemaCreator
from litestar.datastructures import ResponseHeader, UploadFile
from litestar.dto import DataclassDTO
from litestar.exceptions import ImproperlyConfiguredException, LitestarWarning
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import Example, Reference, Schema
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.params import Body, FromQuery, JSONBody, MultipartBody, QueryParameter
from litestar.plugins import OpenAPISchemaPlugin
from litestar.typing import FieldDefinition
from tests.helpers import PREFIX, body_schema, components, document, normalise_json_schema, response_schema, route

T = TypeVar("T")


@dataclasses.dataclass
class Marker:
    value: int = 0


@dataclasses.dataclass
class Other:
    name: str = ""


@dataclasses.dataclass
class Foreign:
    name: str = ""


@dataclasses.dataclass
class Named:
    __schema_name__ = "S"


@dataclasses.dataclass
class Box(Generic[T]):
    __schema_name__ = "B"
    item: T


class ExistingThing:
    pass


Resolve = Callable[[Sequence[LibraryRequest], LibraryRun], LibraryResult]


class FakeResolver(LibraryResolver):
    name = "fake"

    def __init__(self) -> None:
        self.resolve_with: Resolve = MSGSPEC_RESOLVER.resolve

    def resolve(self, requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
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

    def is_plugin_supported_field(self, field_definition: FieldDefinition) -> bool:
        return field_definition.annotation in self.types

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        self.records[field_definition.annotation] = (schema_creator.schema_mode, schema_creator.library_models)
        return Schema(type=OpenAPIType.STRING)


MARKER_DEF: dict[str, Any] = {"type": "object", "properties": {"value": {"type": "integer"}}}
OTHER_DEF: dict[str, Any] = {"type": "object", "properties": {"name": {"type": "string"}}}


def by_name(request: LibraryRequest) -> str:
    return cast("str", request.annotation.__name__)


def canned(
    defs: dict[str, Any],
    names: dict[str, str] | None = None,
    root: Callable[[LibraryRequest], str] = by_name,
) -> Resolve:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        return LibraryResult(
            roots={request: root(request) for request in requests},
            defs=copy.deepcopy(defs),
            names=dict(names or {}),
        )

    return resolver


def in_rounds(*resolvers: Resolve, calls: list[list[LibraryRequest]] | None = None) -> Resolve:
    seen: list[list[LibraryRequest]] = [] if calls is None else calls

    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        seen.append(list(requests))
        return resolvers[len(seen) - 1](requests, run)

    return resolver


def delegating_other(defs: dict[str, Any], mode: SchemaMode = "validation", target: Any = Other) -> Resolve:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        other = run.embed(run.schema_creator(mode).for_field_definition(FieldDefinition.from_annotation(target)))
        resolved = copy.deepcopy(defs)
        resolved["Marker"]["properties"]["other"] = other
        return LibraryResult(roots={request: by_name(request) for request in requests}, defs=resolved)

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
        ({"minimun": 1}, "minimun", {}),
        (
            {"type": "object", "properties": {"a": {"minimun": 1}}},
            "minimun",
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

    def resolver(received: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        requests.extend(received)
        return LibraryResult(roots=dict.fromkeys(received, "X"), defs={"X": {}})

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


@pytest.mark.parametrize(
    ("annotation", "kwarg_definition", "name"),
    [
        (Marker, Body(schema_component_key="k"), "k"),
        (Named, None, None),
        (Named, Body(schema_component_key="k"), "k"),
        (Marker, None, None),
        (Box[int], None, None),
    ],
)
def test_request_name_precedence(
    annotation: Any, kwarg_definition: Any, name: Optional[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    creator = SchemaCreator()
    creator.for_library(FieldDefinition.from_annotation(annotation, kwarg_definition=kwarg_definition), FOREIGN)
    assert captured_requests(creator, monkeypatch) == [LibraryRequest(annotation, FOREIGN, "validation", name)]


def test_named_requests_are_distinct(monkeypatch: pytest.MonkeyPatch) -> None:
    creator = SchemaCreator()
    for key in ("a", "b", "a", None):
        creator.for_library(
            FieldDefinition.from_annotation(Marker, kwarg_definition=Body(schema_component_key=key)), FAKE
        )
    assert [request.name for request in captured_requests(creator, monkeypatch)] == ["a", "b", None]


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


def test_resolution_needing_one_round_more_than_the_cap_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    use_two_rounds(monkeypatch, cap=1)

    with pytest.raises(ImproperlyConfiguredException, match=r"most recently \[<class '.*Other'>\]"):
        fake_document([get_marker()])


def test_resolve_stops_when_requests_never_settle(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        fresh = run.embed(
            run.schema_creator("validation").for_field_definition(FieldDefinition.from_annotation(ExistingThing))
        )
        return LibraryResult(
            roots=dict.fromkeys(requests, "Def"), defs={"Def": {"type": "object", "properties": {"x": fresh}}}
        )

    use(monkeypatch, resolver)

    with pytest.raises(
        ImproperlyConfiguredException,
        match=r"did not settle after 1000 resolution rounds: every round gave the fake schema resolver new types "
        r"to document, most recently \[<class '.*Fresh'>\]",
    ):
        fake_document([get_marker()], plugins=[FreshTypePlugin()])


def test_recursion_error_names_the_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        raise RecursionError

    use(monkeypatch, resolver)

    with pytest.raises(ImproperlyConfiguredException, match="The fake schema resolver exceeded the maximum recursion"):
        fake_document([get_marker()])


def test_run_schema_creator_generates_no_examples(monkeypatch: pytest.MonkeyPatch) -> None:
    creators: dict[str, SchemaCreator] = {}

    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        creators["validation"] = run.schema_creator("validation")
        creators["serialization"] = run.schema_creator("serialization")
        return LibraryResult(roots=dict.fromkeys(requests, "Marker"), defs={"Marker": MARKER_DEF})

    use(monkeypatch, resolver)

    plugin = FakeLibraryPlugin()
    Litestar(
        [get_marker()], plugins=[plugin], openapi_config=OpenAPIConfig(title="t", version="1", create_examples=True)
    ).openapi_schema.to_schema()

    assert {mode: (creator.generate_examples, creator.prefer_alias) for mode, creator in creators.items()} == {
        "validation": (False, True),
        "serialization": (False, False),
    }
    for mode, creator in creators.items():
        assert creator.schema_mode == mode
        assert creator.schema_registry.library.is_placeholder(Reference(f"{library_components._PLACEHOLDER_PREFIX}0"))
    assert plugin.references[0].ref == f"{PREFIX}Marker"


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


def referencing(ref: str) -> Resolve:
    return canned({"Marker": {"type": "object", "properties": {"m": {"$ref": ref}}}})


@pytest.mark.parametrize(
    ("resolver", "match"),
    [
        (referencing("#/$defs/Missing"), "Cannot resolve '#/\\$defs/Missing'"),
        (referencing("https://example.org/schema"), "Cannot resolve 'https://example.org/schema'"),
    ],
)
def test_invalid_resolver_output_raises(resolver: Resolve, match: str, monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, resolver)

    with pytest.raises(ImproperlyConfiguredException, match=match):
        fake_document([get_marker()])


def test_identical_defs_are_emitted_once(monkeypatch: pytest.MonkeyPatch) -> None:
    root = {"type": "object", "properties": {"s": {"$ref": "#/$defs/Inner"}}}
    use(
        monkeypatch,
        canned(
            {"A": root, "B": root, "Inner": {"type": "string"}},
            root=lambda request: "A" if request.annotation is Marker else "B",
        ),
    )

    doc = fake_document([route(keyed("Same"), None, "/marker"), route(keyed("Same", Other), None, "/other")])

    assert sorted(components(doc)) == ["Inner", "Same"]
    assert body_schema(doc, "/marker") == body_schema(doc, "/other") == {"$ref": f"{PREFIX}Same"}
    assert components(doc)["Same"]["properties"]["s"] == {"$ref": f"{PREFIX}Inner"}


def test_same_base_name_in_another_library_gets_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    address = {"type": "object", "properties": {"city": {"$ref": "#/$defs/City"}}}
    use(
        monkeypatch,
        in_rounds(
            delegating_other(
                {
                    "Marker": {
                        "type": "object",
                        "properties": {"s": {"$ref": "#/$defs/Shared"}, "a": {"$ref": "#/$defs/Address"}},
                    },
                    "Shared": {"type": "string"},
                    "Address": address,
                    "City": {"type": "string"},
                },
                target=Foreign,
            ),
            canned(
                {
                    "Foreign": {
                        "type": "object",
                        "properties": {"s": {"$ref": "#/$defs/Shared"}, "a": {"$ref": "#/$defs/Address"}},
                    },
                    "Shared": {"type": "integer"},
                    "Address": address,
                    "City": {"type": "integer"},
                }
            ),
        ),
    )

    schemas = components(fake_document([get_marker()], plugins=[ForeignPlugin()]))

    assert sorted(schemas) == ["Address", "Address_2", "City", "City_2", "Foreign", "Marker", "Shared", "Shared_2"]
    assert schemas["Marker"]["properties"] == {
        "s": {"$ref": f"{PREFIX}Shared"},
        "a": {"$ref": f"{PREFIX}Address"},
        "other": {"$ref": f"{PREFIX}Foreign"},
    }
    assert schemas["Foreign"]["properties"] == {"s": {"$ref": f"{PREFIX}Shared_2"}, "a": {"$ref": f"{PREFIX}Address_2"}}
    assert schemas["Shared"] == {"type": "string"}
    assert schemas["Shared_2"] == {"type": "integer"}
    assert schemas["Address"]["properties"]["city"] == {"$ref": f"{PREFIX}City"}
    assert schemas["Address_2"]["properties"]["city"] == {"$ref": f"{PREFIX}City_2"}


def by_mode(request: LibraryRequest) -> str:
    return "Marker-Input" if request.mode == "validation" else "Marker-Output"


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
            canned({"Marker": MARKER_DEF, "Other": MARKER_DEF}),
            keyed("Custom", Other),
            {"Custom": MARKER_DEF},
            ("Custom", "Custom"),
            id="same-key-identical-schema",
        ),
    ],
)
def test_named_request_components(
    resolver: Resolve,
    response: Any,
    expected: dict[str, Any],
    refs: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use(monkeypatch, resolver)

    doc = fake_document([route(keyed("Custom"), response)])

    assert components(doc) == expected
    assert body_schema(doc) == {"$ref": f"{PREFIX}{refs[0]}"}
    assert response_schema(doc) == {"$ref": f"{PREFIX}{refs[1]}"}


@pytest.mark.parametrize(
    "resolver",
    [
        pytest.param(canned({"Marker": MARKER_DEF}), id="alone"),
        pytest.param(
            canned({"Marker-Input": MARKER_DEF}, root=lambda request: "Marker-Input"), id="alone-drops-suffix"
        ),
    ],
)
def test_named_request_component_used_alone(resolver: Resolve, monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, resolver)

    doc = fake_document([route(keyed("Custom"), None)])

    assert components(doc) == {"Custom": MARKER_DEF}
    assert body_schema(doc) == {"$ref": f"{PREFIX}Custom"}


def test_explicit_name_collision_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, canned({"Marker": MARKER_DEF, "Other": OTHER_DEF}))
    with pytest.raises(ImproperlyConfiguredException, match="Schema component keys must be unique"):
        fake_document([route(keyed("K"), keyed("K", Other))])

    with pytest.raises(ImproperlyConfiguredException, match="Schema component keys must be unique"):
        fake_document([route(keyed("ExistingThing"), ExistingThing)], plugins=[ExistingPlugin()])


def test_explicit_name_wins_over_an_earlier_automatic_name(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        named_other = FieldDefinition.from_annotation(Other, kwarg_definition=Body(schema_component_key="Foo"))
        foo = copy.deepcopy(MARKER_DEF)
        foo["properties"]["other"] = run.embed(run.schema_creator("validation").for_field_definition(named_other))
        return LibraryResult(
            roots={request: "Foo" if request.annotation is Marker else "Other" for request in requests},
            defs={"Foo": foo, "Other": OTHER_DEF},
        )

    use(monkeypatch, resolver)

    schemas = components(fake_document([get_marker()]))

    assert sorted(schemas) == ["Foo", "Foo_2"]
    assert schemas["Foo"] == OTHER_DEF
    assert schemas["Foo_2"]["properties"]["other"] == {"$ref": f"{PREFIX}Foo"}


def test_result_name_wins_over_an_automatic_name(monkeypatch: pytest.MonkeyPatch) -> None:
    use(
        monkeypatch,
        canned(
            {"Foo": MARKER_DEF, "Zed": OTHER_DEF},
            names={"Zed": "Foo"},
            root=lambda request: "Foo" if request.annotation is Marker else "Zed",
        ),
    )

    @get("/marker")
    def marker() -> Marker:
        return Marker()

    @get("/other")
    def other() -> Other:
        return Other()

    doc = fake_document([marker, other])

    assert components(doc) == {"Foo": OTHER_DEF, "Foo_2": MARKER_DEF}
    assert response_schema(doc, "/marker", method="get") == {"$ref": f"{PREFIX}Foo_2"}
    assert response_schema(doc, "/other", method="get") == {"$ref": f"{PREFIX}Foo"}


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

    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        for value in (first, second, first):
            tokens.append(run.embed(Schema(default=value)))
        return LibraryResult(roots=dict.fromkeys(requests, "Marker"), defs={"Marker": MARKER_DEF})

    use(monkeypatch, resolver)
    fake_document([get_marker()])

    assert tokens[0] == tokens[2] != tokens[1]


def test_embedded_existing_reference_gets_final_path(monkeypatch: pytest.MonkeyPatch) -> None:
    tokens: list[dict[str, str]] = []

    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        creator = run.schema_creator("serialization")
        for _ in range(2):
            tokens.append(run.embed(creator.for_field_definition(FieldDefinition.from_annotation(ExistingThing))))
        return LibraryResult(
            roots=dict.fromkeys(requests, "Marker"),
            defs={"Marker": {"type": "object", "properties": {"existing": tokens[0]}}},
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
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
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
        return LibraryResult(
            roots=dict.fromkeys(requests, "Marker"),
            defs={"Marker": {"type": "object", "properties": properties}, "Other": OTHER_DEF},
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


@pytest.mark.parametrize("form", [DcUploadForm, StUploadForm])
def test_optional_upload_file_in_multipart_form_is_a_type_array(form: Any) -> None:
    @post("/", signature_namespace={"form": form})
    async def handler(data: MultipartBody[form]) -> None:  # pyright: ignore[reportInvalidTypeForm]
        return None

    properties = components(fake_document([handler]))[form.__name__]["properties"]

    assert properties["file"] == {"type": "string", "format": "binary", "contentMediaType": "application/octet-stream"}
    assert properties["opt"] == {**properties["file"], "type": ["string", "null"]}


def test_build_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(requests: Sequence[LibraryRequest], run: LibraryRun) -> LibraryResult:
        if any(request.annotation is Marker for request in requests):
            return delegating_other({"Marker": MARKER_DEF, "Other": OTHER_DEF}, mode="serialization", target=Foreign)(
                requests, run
            )
        return canned({"Other": {"type": "string"}}, root=lambda request: "Other")(requests, run)

    use(monkeypatch, resolver)

    app = Litestar(
        [route(JSONBody[Other], Marker)],
        plugins=[FakeLibraryPlugin(), ForeignPlugin()],
        openapi_config=OpenAPIConfig(title="t", version="1"),
    )
    first = json.dumps(app.openapi_schema.to_schema())
    app.plugins.get(OpenAPIPlugin).invalidate_schema_cache()
    second = json.dumps(app.openapi_schema.to_schema())

    assert first == second
    assert "Other_2" in first


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


@dataclasses.dataclass
class DTOModel:
    value: int


DTO_RECORDS: list[tuple[bool, str]] = []


class RecordingDTO(DataclassDTO[DTOModel]):
    @classmethod
    def create_openapi_schema(
        cls, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        DTO_RECORDS.append((schema_creator.library_models, schema_creator.schema_mode))
        return super().create_openapi_schema(field_definition, handler_id, schema_creator)


def test_dto_schemas_use_a_non_library_creator() -> None:
    DTO_RECORDS.clear()

    @post("/", dto=RecordingDTO, return_dto=RecordingDTO)
    def handler(data: JSONBody[DTOModel]) -> DTOModel:
        return data

    Litestar([handler]).openapi_schema.to_schema()

    assert sorted(DTO_RECORDS) == [(False, "serialization"), (False, "validation")]


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


def pair(input_: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    return {"Input": input_, "Output": output}


def refs(target: str, suffix: str) -> dict[str, Any]:
    return {"type": "object", "properties": {"next": {"$ref": f"#/$defs/{target}{suffix}"}}}


@pytest.mark.parametrize(
    ("defs", "expected"),
    [
        pytest.param(
            {"Marker": lambda s: refs("Other", s), "Other": lambda s: refs("Marker", s)},
            {"Marker": refs("Other", ""), "Other": refs("Marker", "")},
            id="mutually-recursive-pair-merges",
        ),
        pytest.param(
            {
                "Marker": lambda s: refs("Middle", s),
                "Middle": lambda s: refs("Split", s),
                "Split": lambda s: {"type": "integer" if s == "-Input" else "string"},
            },
            {
                **{f"Marker{s}": refs("Middle", s) for s in ("-Input", "-Output")},
                **{f"Middle{s}": refs("Split", s) for s in ("-Input", "-Output")},
                "Split-Input": {"type": "integer"},
                "Split-Output": {"type": "string"},
            },
            id="chain-to-a-split-pair-stays-split",
        ),
    ],
)
def test_mode_pairs_merge_unless_they_reach_a_real_difference(
    defs: dict[str, Callable[[str], dict[str, Any]]], expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    generated = {f"{name}{suffix}": make(suffix) for name, make in defs.items() for suffix in ("-Input", "-Output")}
    use(
        monkeypatch,
        canned(generated, root=lambda request: f"Marker{'-Input' if request.mode == 'validation' else '-Output'}"),
    )

    schemas = components(fake_document([route(JSONBody[Marker], Marker)]))

    expected = {name: json.loads(json.dumps(schema).replace("#/$defs/", PREFIX)) for name, schema in expected.items()}
    assert schemas == expected


def test_map_references_drops_a_discriminator_mapping_to_non_references() -> None:
    def rename(ref: str) -> str:
        return ref.upper()

    node = {
        "oneOf": [{"$ref": "a"}],
        "discriminator": {"propertyName": "kind", "mapping": {"a": "a"}},
        "properties": {"inline": {"discriminator": {"propertyName": "kind", "mapping": {"b": {"type": "object"}}}}},
    }

    assert map_references(node, rename) == {
        "oneOf": [{"$ref": "A"}],
        "discriminator": {"propertyName": "kind", "mapping": {"a": "A"}},
        "properties": {"inline": {}},
    }


def test_build_result_rejects_a_root_without_a_schema() -> None:
    request = LibraryRequest(Marker, FAKE, "validation")

    with pytest.raises(
        ImproperlyConfiguredException, match="The fake schema resolver cannot document .*Marker.* as a component"
    ):
        build_result({request: "Missing"}, {"validation": {}}, {}, {})


def test_components_of_an_unresolved_placeholder_raise() -> None:
    @dataclasses.dataclass
    class Point:
        x: int

    creator = SchemaCreator(plugins=openapi_schema_plugins)
    creator.for_field_definition(FieldDefinition.from_annotation(Point))

    with pytest.raises(ImproperlyConfiguredException, match="never resolved"):
        creator.schema_registry.generate_components_schemas()


def test_unique_names_collapse_runs_of_invalid_characters() -> None:
    assert unique_names({"pair": ("Pair[int, str]", "m.Pair[int, str]")}) == {"pair": "Pair_int_str_"}
