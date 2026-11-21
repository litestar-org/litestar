import re
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, NewType, cast, get_args, get_origin, get_type_hints

import pydantic
from pydantic.errors import PydanticInvalidForJsonSchema, PydanticUserError
from pydantic.json_schema import CoreRef, GenerateJsonSchema, JsonSchemaValue, _DefinitionsRemapping
from pydantic_core import core_schema

from litestar._openapi.schema_generation.library import (
    LOCAL_PREFIX,
    MODES,
    LibraryRequest,
    LibraryResolver,
    LibraryRun,
    claimed_by_other_plugin,
    kwarg_definition_metadata,
    map_references,
)
from litestar._openapi.schema_generation.library.exceptions import SchemaConversionError
from litestar._openapi.schema_generation.library.graph import (
    NameCandidates,
    ResolvedSchemas,
    SchemaKey,
    SchemaNode,
    schema_node,
)
from litestar.dto.field import DTO_FIELD_META_KEY
from litestar.plugins.pydantic import _model_dump
from litestar.plugins.pydantic.plugins.init import PydanticInitPlugin
from litestar.plugins.pydantic.plugins.schema import PydanticSchemaPlugin
from litestar.plugins.pydantic.utils import is_pydantic_model_instance
from litestar.typing import FieldDefinition, TypeAliasTypes

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic._internal._core_utils import CoreSchemaOrField

__all__ = ("PYDANTIC_RESOLVER", "LitestarGenerateJsonSchema")

_EMBED_KEY = "x-litestar-embed"
_INLINE_KEY = "x-litestar-inline"
_NAME_KEY = "x-litestar-schema-name"
_TYPE_REF_PARTS = re.compile(r"([\][,])")
_MODULE_PATH = re.compile(r"(?:[^.[\]]+\.)+([^.[\]]+)")
_IDENTITY_KEYS = frozenset(("metadata", "ref"))
_UNHASHABLE = object()
_KEEP: Any = object()
_JSON_TYPES: dict[type, tuple[str, ...]] = {
    bool: ("boolean",),
    int: ("integer", "number"),
    float: ("number",),
    str: ("string",),
    list: ("array",),
    dict: ("object",),
    type(None): ("null",),
}


def _accepted_aliases(field: Mapping[str, Any]) -> list[str]:
    alias = field.get("validation_alias")
    if isinstance(alias, str):
        return [alias]
    return [path[0] for path in alias or () if isinstance(path, list) and len(path) == 1 and isinstance(path[0], str)]


def _document_accepted_keys(
    result: JsonSchemaValue, fields: Iterable[tuple[str, Mapping[str, Any]]], config: Mapping[str, Any]
) -> JsonSchemaValue:
    by_name = config.get("validate_by_name") or config.get("populate_by_name")
    by_alias = config.get("validate_by_alias", True)
    properties: dict[str, Any] = result.get("properties", {})
    required: list[str] = result.get("required", [])
    for name, field in fields:
        aliases = _accepted_aliases(field)
        emitted = aliases[0] if aliases else name
        accepted = [*aliases] if by_alias else []
        if by_name or not aliases:
            accepted.append(name)
        keys = list(dict.fromkeys(accepted))
        if keys == [emitted] or emitted not in properties:
            continue
        result["properties"] = properties = {
            new: value for key, value in properties.items() for new in (keys if key == emitted else (key,))
        }
        if emitted in required:
            position = required.index(emitted)
            if len(keys) == 1:
                required[position] = keys[0]
            else:
                del required[position]
                result.setdefault("allOf", []).append({"anyOf": [{"required": [key]} for key in keys]})
    if "required" in result and not required:
        del result["required"]
    return result


def _without_dto_metadata(result: JsonSchemaValue) -> JsonSchemaValue:
    for value in result.get("properties", {}).values():
        if isinstance(value, dict):
            value.pop(DTO_FIELD_META_KEY, None)
    return result


def _without_unique_items(result: JsonSchemaValue) -> JsonSchemaValue:
    result.pop("uniqueItems", None)
    return result


def _matches_type(value: Any, documented: Any) -> bool:
    if documented is None:
        return True
    accepted = {documented} if isinstance(documented, str) else set(documented)
    return not accepted.isdisjoint(_JSON_TYPES.get(type(value), accepted))


def _alias_value(alias: Any, arguments: tuple[Any, ...]) -> Any:
    value = alias.__value__
    if not arguments:
        return value
    if getattr(value, "__parameters__", ()):
        try:
            return value[arguments]
        except TypeError:
            return value
    pairs = zip(alias.__type_params__, arguments, strict=False)
    return next((argument for parameter, argument in pairs if parameter is value), value)


def _visit_key(node: Any) -> Any:
    try:
        hash(node)
    except TypeError:
        return _UNHASHABLE, id(node)
    return node


def _nested_annotations(annotation: Any) -> Iterator[Any]:
    seen: set[Any] = set()

    def walk(node: Any, expanding: frozenset[Any]) -> Iterator[Any]:
        if (key := _visit_key(node)) in seen:
            return
        seen.add(key)
        yield node
        origin = get_origin(node)
        alias = next((value for value in (node, origin) if isinstance(value, TypeAliasTypes)), None)
        if alias is not None and alias not in expanding:
            try:
                value = _alias_value(alias, get_args(node) if alias is origin else ())
            except NameError:
                pass
            else:
                yield from walk(value, expanding | {alias})
        if isinstance(node, NewType):
            yield from walk(node.__supertype__, expanding)
        for argument in get_args(node):
            yield from walk(argument, expanding)

    return walk(annotation, frozenset())


def _field_annotation(owner: Any, name: str | None) -> Any:
    if owner is None or name is None:
        return None
    if (field := getattr(owner, "__pydantic_fields__", {}).get(name)) is not None:
        return field.annotation
    decorators = getattr(owner, "__pydantic_decorators__", None)
    if decorators is not None and name in decorators.computed_fields:
        return decorators.computed_fields[name].info.return_type
    try:
        return get_type_hints(owner, include_extras=True).get(name)
    except (NameError, TypeError):
        return None


def _field_metadata(owner: Any, name: str | None) -> Sequence[Any]:
    if (field := getattr(owner, "__pydantic_fields__", {}).get(name)) is not None:
        return cast("Sequence[Any]", field.metadata)
    return getattr(_field_annotation(owner, name), "__metadata__", ())


def _fingerprint(node: Any) -> Any:
    if isinstance(node, dict):
        return tuple(sorted((key, _fingerprint(value)) for key, value in node.items() if key not in _IDENTITY_KEYS))
    if isinstance(node, list):
        return tuple(_fingerprint(item) for item in node)
    if isinstance(node, type) or not callable(node):
        return node
    return getattr(getattr(node, "__func__", node), "__code__", node)


def _qualnames(classes: Iterable[type]) -> str:
    return ", ".join(cls.__qualname__ for cls in classes)


def _field_names(fields: Iterable[tuple[str, Any]], schema: Mapping[str, Any]) -> dict[int, str]:
    computed = [(field["property_name"], field) for field in schema.get("computed_fields", ())]
    return {id(field): name for name, field in (*fields, *computed)}


class LitestarGenerateJsonSchema(GenerateJsonSchema):
    def __init__(
        self, run: LibraryRun, prefer_alias: bool, roots: Collection[Any] = (), ref_template: str = "#/$defs/{model}"
    ) -> None:
        self._run = run
        self._roots = roots
        self._dataclass_config: Mapping[str, Any] = {}
        self._owner: Any = None
        self._field: str | None = None
        self._field_names: Mapping[int, str] = {}
        self._core_fingerprints: dict[type, Any] = {}
        self._shared: Sequence[tuple[Any, str | None]] = ()
        self._ref_contexts: dict[str, list[tuple[Any, str | None]]] = {}
        self.warnings: dict[str, None] = {}
        super().__init__(by_alias=True, ref_template=ref_template)
        self._serialization_by_alias = prefer_alias

    @property
    def by_alias(self) -> bool:
        return self.mode == "validation" or self._serialization_by_alias

    @by_alias.setter
    def by_alias(self, value: bool) -> None:
        self._serialization_by_alias = value

    def _build_definitions_remapping(self) -> _DefinitionsRemapping:
        return _DefinitionsRemapping({}, {})

    def definitions_schema(self, schema: core_schema.DefinitionsSchema) -> JsonSchemaValue:
        result = self.generate_inner(schema["schema"])
        remaining = {definition["ref"]: definition for definition in schema["definitions"]}  # type: ignore[typeddict-item]
        while remaining:
            ready = [ref for ref in remaining if ref in self._ref_contexts] or list(remaining)
            for ref in ready:
                (owner, field), *shared = self._ref_contexts.get(ref, [(None, None)])
                with self._scope(owner=owner, field=field, shared=shared):
                    try:
                        self.generate_inner(remaining.pop(ref))
                    except PydanticInvalidForJsonSchema as exc:
                        self._core_defs_invalid_for_json_schema[self.get_defs_ref((CoreRef(ref), self.mode))] = exc
        return result

    def definition_ref_schema(self, schema: core_schema.DefinitionReferenceSchema) -> JsonSchemaValue:
        contexts = self._ref_contexts.setdefault(schema["schema_ref"], [])
        if (context := (self._owner, self._field)) not in contexts:
            contexts.append(context)
        return super().definition_ref_schema(schema)

    def set_schema(self, schema: core_schema.SetSchema) -> JsonSchemaValue:
        return _without_unique_items(super().set_schema(schema))

    def frozenset_schema(self, schema: core_schema.FrozenSetSchema) -> JsonSchemaValue:
        return _without_unique_items(super().frozenset_schema(schema))

    def bytes_schema(self, schema: core_schema.BytesSchema) -> JsonSchemaValue:
        result = super().bytes_schema(schema)
        setting = self._config.config_dict.get(
            "val_json_bytes" if self.mode == "validation" else "ser_json_bytes", "utf8"
        )
        if setting == "base64":
            result["format"] = "base64url"
        else:
            result.pop("format", None)
        return result

    def default_schema(self, schema: core_schema.WithDefaultSchema) -> JsonSchemaValue:
        result = super().default_schema(schema)
        if (
            self.mode == "serialization"
            and "default" in result
            and not _matches_type(result["default"], result.get("type"))
        ):
            del result["default"]
        return result

    def model_fields_schema(self, schema: core_schema.ModelFieldsSchema) -> JsonSchemaValue:
        return self._fields_schema(
            super().model_fields_schema, schema, list(schema["fields"].items()), self._config.config_dict
        )

    def model_field_schema(self, schema: core_schema.ModelField) -> JsonSchemaValue:
        return self._in_field(super().model_field_schema, schema)

    def dataclass_field_schema(self, schema: core_schema.DataclassField) -> JsonSchemaValue:
        return self._in_field(super().dataclass_field_schema, schema)

    def typed_dict_field_schema(self, schema: core_schema.TypedDictField) -> JsonSchemaValue:
        return self._in_field(super().typed_dict_field_schema, schema)

    def computed_field_schema(self, schema: core_schema.ComputedField) -> JsonSchemaValue:
        return self._in_field(super().computed_field_schema, schema)

    def dataclass_args_schema(self, schema: core_schema.DataclassArgsSchema) -> JsonSchemaValue:
        fields = [(field["name"], field) for field in schema["fields"]]
        return self._fields_schema(super().dataclass_args_schema, schema, fields, self._dataclass_config)

    def dataclass_schema(self, schema: core_schema.DataclassSchema) -> JsonSchemaValue:
        if self._claimed_by_other_plugin(schema["cls"]):
            return self._inline(schema["cls"])
        with self._scope(dataclass_config=schema.get("config", {}), owner=schema["cls"], field=None, shared=()):
            return super().dataclass_schema(schema)

    def typed_dict_schema(self, schema: core_schema.TypedDictSchema) -> JsonSchemaValue:
        if (cls := schema.get("cls")) is not None and self._claimed_by_other_plugin(cls):
            return self._inline(cls)
        with self._scope(owner=cls, field=None, shared=()):
            return self._fields_schema(
                super().typed_dict_schema, schema, list(schema["fields"].items()), schema.get("config", {})
            )

    def is_instance_schema(self, schema: core_schema.IsInstanceSchema) -> JsonSchemaValue:
        cls = schema["cls"]
        parametrised: list[Any] = []
        for node in self._context_annotations():
            if get_origin(node) is cls and not getattr(node, "__parameters__", ()) and node not in parametrised:
                parametrised.append(node)
        return self._embed(parametrised[0] if len(parametrised) == 1 else cls)

    def enum_schema(self, schema: core_schema.EnumSchema) -> JsonSchemaValue:
        return self._inline(schema["cls"])

    def model_schema(self, schema: core_schema.ModelSchema) -> JsonSchemaValue:
        cls = schema["cls"]
        if self._claimed_by_other_plugin(cls):
            return self._inline(cls)
        try:
            with self._scope(owner=cls, field="root" if schema.get("root_model") else None, shared=()):
                result = super().model_schema(schema)
        except KeyError as exc:
            raise SchemaConversionError(
                f"Cannot document {cls.__qualname__!r}: pydantic cannot resolve the JSON schema reference {exc}"
            ) from exc
        if isinstance(name := cls.__dict__.get("__schema_name__"), str):
            result[_NAME_KEY] = name
            if "title" not in cls.model_config and result.get("title") == cls.__name__:
                result["title"] = name
        return result

    def field_title_should_be_set(self, schema: "CoreSchemaOrField") -> bool:
        if schema["type"] == "is-instance":
            return False
        return super().field_title_should_be_set(schema)

    def handle_invalid_for_json_schema(self, schema: "CoreSchemaOrField", error_info: str) -> JsonSchemaValue:
        claimed = [
            cls for cls in self._context_annotations() if isinstance(cls, type) and self._claimed_by_other_plugin(cls)
        ]
        target = _fingerprint(schema)
        matches = [cls for cls in claimed if self._core_fingerprint(cls) == target]
        if len(matches) == 1:
            return self._embed(matches[0])
        owner = getattr(self._owner, "__qualname__", None)
        if owner is None:
            where = "a type"
        elif self._field is None:
            where = f"a field of {owner!r}"
        else:
            where = f"the field {self._field!r} of {owner!r}"
        if not claimed:
            reason = "no schema plugin documents its type"
        elif matches:
            reason = f"it matches several types schema plugins document ({_qualnames(matches)})"
        else:
            reason = f"it matches none of the types schema plugins document in it ({_qualnames(claimed)})"
        self.warnings[
            f"Pydantic cannot generate a JSON schema for {where} and {reason}, so it is documented as any value"
        ] = None
        return {}

    @contextmanager
    def _scope(
        self,
        *,
        owner: Any = _KEEP,
        field: str | None = _KEEP,
        shared: Sequence[tuple[Any, str | None]] = _KEEP,
        field_names: Mapping[int, str] = _KEEP,
        dataclass_config: Mapping[str, Any] = _KEEP,
    ) -> Iterator[None]:
        candidates = {
            "_owner": owner,
            "_field": field,
            "_shared": shared,
            "_field_names": field_names,
            "_dataclass_config": dataclass_config,
        }
        values = {name: value for name, value in candidates.items() if value is not _KEEP}
        outer = {name: getattr(self, name) for name in values}
        for name, value in values.items():
            setattr(self, name, value)
        try:
            yield
        finally:
            for name, value in outer.items():
                setattr(self, name, value)

    def _fields_schema(
        self,
        generate: "Callable[[Any], JsonSchemaValue]",
        schema: Any,
        fields: list[tuple[str, Any]],
        config: Mapping[str, Any],
    ) -> JsonSchemaValue:
        with self._scope(field_names=_field_names(fields, schema)):
            result = _without_dto_metadata(generate(schema))
        if self.mode != "validation":
            return result
        return _document_accepted_keys(result, fields, config)

    def _in_field(self, generate: "Callable[[Any], JsonSchemaValue]", schema: Any) -> JsonSchemaValue:
        with self._scope(field=self._field_names.get(id(schema), self._field)):
            result = generate(schema)
            metadata = kwarg_definition_metadata(_field_metadata(self._owner, self._field), self._run.serializer)
        return {**metadata, **result} if metadata else result

    def _context_annotations(self) -> list[Any]:
        contexts = ((self._owner, self._field), *self._shared)
        annotations = [annotation for context in contexts if (annotation := _field_annotation(*context)) is not None]
        if not annotations:
            return []
        first, *others = annotations
        nodes = list(_nested_annotations(first))
        for other in others:
            reached = {_visit_key(node) for node in _nested_annotations(other)}
            nodes = [node for node in nodes if _visit_key(node) in reached]
        return nodes

    def _core_fingerprint(self, cls: type) -> Any:
        if cls not in self._core_fingerprints:
            try:
                self._core_fingerprints[cls] = _fingerprint(pydantic.TypeAdapter(cls).core_schema)
            except pydantic.PydanticUserError:
                self._core_fingerprints[cls] = None
        return self._core_fingerprints[cls]

    def _embed(self, annotation: Any) -> JsonSchemaValue:
        result = self._run.schema_creator(self.mode).for_field_definition(FieldDefinition.from_annotation(annotation))
        return {_EMBED_KEY: self._run.embed(result)["$ref"]}

    def _inline(self, cls: Any) -> JsonSchemaValue:
        return {_INLINE_KEY: self._embed(cls)[_EMBED_KEY]}

    def _claimed_by_other_plugin(self, cls: Any) -> bool:
        return cls not in self._roots and claimed_by_other_plugin(
            self._run.schema_creator(self.mode), cls, PydanticSchemaPlugin.to_openapi_schema
        )


def _rewrite(node: Any, targets: Mapping[str, str]) -> Any:
    return map_references(node, lambda ref: targets.get(ref, ref), (_EMBED_KEY, _INLINE_KEY))


def _replacement(schema: JsonSchemaValue) -> str | None:
    target: str | None = schema.get(_INLINE_KEY)
    if target is None and schema.keys() == {_EMBED_KEY}:
        target = schema[_EMBED_KEY]
    return target


def _class_names(core_ref: str) -> tuple[str, str]:
    parts = [part.rsplit(":", 1)[0] for part in _TYPE_REF_PARTS.split(core_ref)]
    return "".join(_MODULE_PATH.sub(r"\1", part) for part in parts), "".join(parts)


def _input_value(model: pydantic.BaseModel) -> Any:
    for by_alias in (True, False):
        value = _model_dump(model, by_alias=by_alias, round_trip=True)
        try:
            accepted = type(model).model_validate(value, strict=False)
        except ValueError:
            continue
        if _model_dump(accepted, by_alias=by_alias, round_trip=True) == value:
            return value
    raise ValueError(f"No JSON dump of {model!r} passes validation")


class _PydanticResolver(LibraryResolver):
    name = "pydantic"

    def resolve(self, requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        prefer_alias = next(
            (plugin.prefer_alias for plugin in run.init_plugins if isinstance(plugin, PydanticInitPlugin)), False
        )
        generator = LitestarGenerateJsonSchema(
            run, prefer_alias=prefer_alias, roots={request.annotation for request in requests}
        )
        try:
            keys, generated = generator.generate_definitions(
                [(request, request.mode, request.annotation.__pydantic_core_schema__) for request in requests]
            )
        except PydanticUserError as exc:
            raise SchemaConversionError(f"Cannot document a pydantic model: {exc.message}") from exc

        inlined = {
            f"{LOCAL_PREFIX}{ref}": target
            for ref, schema in generated.items()
            if (target := _replacement(schema)) is not None
        }
        targets: dict[str, SchemaKey] = {}
        schemas: dict[SchemaKey, dict[str, Any]] = {}
        identities: dict[str, None] = {}
        schema_names: dict[str, str] = {}
        for ref, generated_schema in generated.items():
            if f"{LOCAL_PREFIX}{ref}" in inlined:
                continue
            core_ref, mode = generator.defs_to_core_refs[ref]
            targets[f"{LOCAL_PREFIX}{ref}"] = key = SchemaKey(self.name, core_ref, mode)
            identities[core_ref] = None
            schema = _rewrite(generated_schema, inlined)
            if (name := schema.pop(_NAME_KEY, None)) is not None:
                schema_names[core_ref] = name
            schemas[key] = schema

        nodes: dict[SchemaKey, SchemaNode] = {}
        for identity in sorted(identities, key=lambda core_ref: core_ref in schema_names):
            names = NameCandidates(*_class_names(identity), explicit=schema_names.get(identity))
            for mode, _ in MODES:
                if (key := SchemaKey(self.name, identity, mode)) in schemas:
                    nodes[key] = schema_node(schemas[key], targets, names)
        roots = {
            request: targets[root_ref]
            for request in requests
            if isinstance(root_ref := keys[(request, request.mode)].get("$ref"), str) and root_ref in targets
        }
        return ResolvedSchemas(roots, nodes, tuple(generator.warnings))

    def to_input_example(self, value: Any) -> Any:
        if is_pydantic_model_instance(value):
            return _input_value(value)
        return super().to_input_example(value)


PYDANTIC_RESOLVER = _PydanticResolver()
