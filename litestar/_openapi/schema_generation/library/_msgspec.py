# pyright: reportUnnecessaryTypeIgnoreComment=false

from collections.abc import Callable, Collection, Sequence
from typing import TYPE_CHECKING, Any, Literal

import msgspec
import msgspec.inspect
import msgspec.json
import msgspec.msgpack
import msgspec.structs
from msgspec import _json_schema

from litestar._openapi.schema_generation.library import (
    LOCAL_PREFIX,
    MODES,
    LibraryRequest,
    LibraryResolver,
    LibraryRun,
    SchemaMode,
    claimed_by_other_plugin,
    kwarg_definition_metadata,
)
from litestar._openapi.schema_generation.library.exceptions import SchemaConversionError
from litestar._openapi.schema_generation.library.graph import (
    NameCandidates,
    ResolvedSchemas,
    SchemaKey,
    SchemaNode,
    reachable,
    schema_node,
)
from litestar.serialization import default_serializer
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar.types import Serializer

__all__ = ("MSGSPEC_RESOLVER", "supports_msgspec_schema")

_DEFAULTED_TYPES = (msgspec.inspect.StructType, msgspec.inspect.DataclassType, msgspec.inspect.NamedTupleType)


class _LitestarTranslator(msgspec.inspect._Translator):
    def __init__(self, types: Sequence[Any], serializer: "Serializer" = default_serializer) -> None:
        super().__init__(types)  # type: ignore[no-untyped-call]
        self.serializer = serializer

    def translate(self, typ: Any) -> msgspec.inspect.Type:
        result: msgspec.inspect.Type = super().translate(typ)  # type: ignore[no-untyped-call]
        if metadata := kwarg_definition_metadata(getattr(typ, "__metadata__", ()), self.serializer):
            return msgspec.inspect.Metadata(result, extra_json_schema=metadata)
        return result

    def _translate_inner(self, t: Any, args: Any, **constraints: Any) -> msgspec.inspect.Type:  # type: ignore[override]
        if t is Literal:
            return msgspec.inspect.LiteralType(tuple(args))
        return super()._translate_inner(t, args, **constraints)  # type: ignore[no-untyped-call,no-any-return]


def supports_msgspec_schema(annotation: Any) -> bool:
    try:
        msgspec.msgpack.Decoder(annotation)
    except (TypeError, NameError):
        return False
    except RecursionError as exc:
        raise SchemaConversionError(
            f"Cannot document {annotation!r}: msgspec exceeds the maximum recursion depth decoding it"
        ) from exc
    return True


def _unwrap(t: msgspec.inspect.Type) -> tuple[msgspec.inspect.Type, dict[str, Any]]:
    extra: dict[str, Any] = {}
    while isinstance(t, msgspec.inspect.Metadata):
        extra.update(t.extra_json_schema or {})
        t = t.type
    return t, extra


def _documented_default(value: Any, serializer: "Serializer") -> Any:
    if value is msgspec.NODEFAULT:
        return value
    try:
        return msgspec.json.decode(msgspec.json.encode(value, enc_hook=serializer, order="deterministic"))
    except (TypeError, ValueError, msgspec.MsgspecError):
        return msgspec.NODEFAULT


class _LitestarSchemaGenerator(_json_schema._SchemaGenerator):
    def __init__(
        self,
        name_map: dict[Any, str],
        mode: SchemaMode,
        delegated: Collection[Any],
        delegate: Callable[[Any], dict[str, Any]],
        serializer: "Serializer",
    ) -> None:
        super().__init__(name_map, None, f"{LOCAL_PREFIX}{{name}}")
        self.mode = mode
        self.delegated = delegated
        self.delegate = delegate
        self.serializer = serializer

    def to_schema(self, t: msgspec.inspect.Type, check_ref: bool = True) -> dict[str, Any]:
        inner, extra = _unwrap(t)
        cls = getattr(inner, "cls", None)
        if isinstance(inner, (msgspec.inspect.CustomType, msgspec.inspect.EnumType)) or cls in self.delegated:
            return {**self.delegate(cls), **extra}
        if isinstance(inner, msgspec.inspect.ExtType):
            return extra
        if isinstance(inner, msgspec.inspect.UnionType) and any(
            isinstance(member := _unwrap(subtype)[0], msgspec.inspect.StructType) and member.cls in self.delegated
            for subtype in inner.types
        ):
            return {**extra, "anyOf": [self.to_schema(subtype) for subtype in inner.types]}
        if (
            isinstance(inner, _DEFAULTED_TYPES)
            and not (check_ref and inner.cls in self.name_map)
            and any(f.default is not msgspec.NODEFAULT for f in inner.fields)
        ):
            fields = tuple(
                msgspec.structs.replace(f, default=_documented_default(f.default, self.serializer))
                for f in inner.fields
            )
            return {**super().to_schema(msgspec.structs.replace(inner, fields=fields), False), **extra}
        if isinstance(inner, msgspec.inspect.LiteralType):
            return {**extra, "enum": list(inner.values)}
        if isinstance(inner, msgspec.inspect.DecimalType) and self.mode == "validation":
            return {**extra, "anyOf": [{"type": "number"}, {"type": "string", "format": "decimal"}]}
        if isinstance(inner, (msgspec.inspect.SetType, msgspec.inspect.FrozenSetType)):
            schema = super().to_schema(inner, check_ref)
            return {**{key: value for key, value in schema.items() if key != "uniqueItems"}, **extra}
        if isinstance(inner, (msgspec.inspect.DateTimeType, msgspec.inspect.TimeType)) and inner.tz is None:
            date_format = "date-time" if isinstance(inner, msgspec.inspect.DateTimeType) else "time"
            return {**super().to_schema(inner, check_ref), "format": date_format, **extra}
        return super().to_schema(t, check_ref)


def _delegate(run: LibraryRun, mode: SchemaMode) -> Callable[[Any], dict[str, Any]]:
    creator = run.schema_creator(mode)
    return lambda cls: run.embed(creator.for_field_definition(FieldDefinition.from_annotation(cls)))


def _qualified_name(cls: Any) -> str:
    return repr(cls) if hasattr(cls, "__origin__") else f"{cls.__module__}.{cls.__qualname__}"


class _MsgspecResolver(LibraryResolver):
    name = "msgspec"

    def resolve(self, requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        translator = _LitestarTranslator([request.annotation for request in requests], run.serializer)
        infos = [_unwrap(info)[0] for info in translator.run()]  # type: ignore[no-untyped-call]
        components = _json_schema._collect_component_types(infos)

        creator = run.schema_creator("validation")
        root_classes = [getattr(info, "cls", None) for info in infos]
        roots = set(root_classes)
        delegated = {
            cls
            for cls, info in components.items()
            if isinstance(info, msgspec.inspect.EnumType)
            or (cls not in roots and claimed_by_other_plugin(creator, cls))
        }
        references = {cls: str(index) for index, cls in enumerate(cls for cls in components if cls not in delegated)}
        names: dict[Any, NameCandidates] = {}
        for cls in references:
            explicit = getattr(cls, "__dict__", {}).get("__schema_name__")
            names[cls] = NameCandidates(
                _json_schema._get_class_name(cls),
                _qualified_name(cls),
                explicit if isinstance(explicit, str) else None,
            )

        kept: dict[SchemaKey, SchemaNode] = {}
        for mode, _ in MODES:
            mode_roots = [cls for request, cls in zip(requests, root_classes, strict=True) if request.mode == mode]
            if not mode_roots:
                continue
            generator = _LitestarSchemaGenerator(references, mode, delegated, _delegate(run, mode), run.serializer)
            targets = {f"{LOCAL_PREFIX}{name}": SchemaKey(self.name, cls, mode) for cls, name in references.items()}
            mode_nodes = {
                SchemaKey(self.name, cls, mode): schema_node(
                    _titled(generator.to_schema(info, False), names[cls].explicit), targets, names[cls]
                )
                for cls, info in _json_schema._collect_component_types(
                    [info for request, info in zip(requests, infos, strict=True) if request.mode == mode]
                ).items()
                if cls in references
            }
            root_keys = [key for cls in mode_roots if (key := SchemaKey(self.name, cls, mode)) in mode_nodes]
            for key in {*root_keys, *reachable(root_keys, mode_nodes)}:
                kept[key] = mode_nodes[key]

        nodes = {
            key: kept[key]
            for cls in references
            for mode, _ in MODES
            if (key := SchemaKey(self.name, cls, mode)) in kept
        }
        return ResolvedSchemas(
            {
                request: SchemaKey(self.name, cls, request.mode)
                for request, cls in zip(requests, root_classes, strict=True)
                if cls in references
            },
            nodes,
        )


def _titled(schema: dict[str, Any], title: str | None) -> dict[str, Any]:
    return schema if title is None else {**schema, "title": title}


MSGSPEC_RESOLVER = _MsgspecResolver()
