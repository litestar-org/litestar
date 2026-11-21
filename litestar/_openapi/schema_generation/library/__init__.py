import math
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, TypeGuard, TypeVar

import msgspec.json

from litestar._openapi.datastructures import INVALID_KEY_CHARACTER_PATTERN
from litestar._openapi.schema_generation.library.converter import EMBED_PREFIX
from litestar._openapi.schema_generation.library.exceptions import SchemaConversionError
from litestar.params import KwargDefinition
from litestar.plugins import OpenAPISchemaPlugin
from litestar.serialization.msgspec_hooks import get_serializer
from litestar.typing import FieldDefinition
from litestar.utils.helpers import unique_name_for_scope

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar._openapi.schema_generation.schema import SchemaCreator
    from litestar.openapi.spec.reference import Reference
    from litestar.openapi.spec.schema import Schema
    from litestar.plugins import InitPluginProtocol
    from litestar.types import Serializer

__all__ = (
    "LOCAL_PREFIX",
    "MODES",
    "LibraryRequest",
    "LibraryResolver",
    "LibraryResult",
    "LibraryRun",
    "MsgspecRoutedPlugin",
    "SchemaMode",
    "build_result",
    "claimed_by_other_plugin",
    "embed_index",
    "kwarg_definition_metadata",
    "local_name",
    "local_references",
    "map_references",
    "msgspec_placeholder",
    "reachable",
    "renamer",
    "routed_to_msgspec",
    "unique_names",
)

SchemaMode = Literal["validation", "serialization"]

_K = TypeVar("_K", bound=Hashable)
LOCAL_PREFIX = "#/$defs/"
MODES: tuple[tuple[SchemaMode, str], ...] = (("validation", "-Input"), ("serialization", "-Output"))


class LibraryResolver(ABC):
    """Generates the schemas of the models a schema plugin defers to a library.

    Requests are grouped by resolver, and resolvers run in the order of their ``name``, which also decides which
    resolver's component keeps a name two resolvers both generate. ``name`` must be non-empty and unique among the
    resolvers used to build one document.
    """

    name: str

    @abstractmethod
    def resolve(self, requests: Sequence["LibraryRequest"], run: "LibraryRun") -> "LibraryResult":
        """Generate the schemas of ``requests``, all the requests made with this resolver so far.

        A resolution round runs the resolver again whenever requests were added since its last run.

        Args:
            requests: The schema requests to resolve.
            run: What the resolver may use during this round.

        Returns:
            The generated schemas, which must cover every request in ``requests``.
        """

    def to_input_example(self, value: Any) -> Any:
        """Convert a model instance in a generated input example to a value validation accepts.

        Args:
            value: The model instance.

        Returns:
            A value validation accepts.

        Raises:
            TypeError: If the resolver cannot convert ``value``.
            ValueError: If no JSON dump of ``value`` passes validation.
        """
        raise TypeError(f"Cannot convert {value!r} to an input value")


@dataclass(frozen=True)
class LibraryRequest:
    """A type whose schema a plugin deferred to ``resolver``, for one mode and component name.

    ``name`` is the explicit component name of the use site, if any.
    """

    annotation: Any
    resolver: LibraryResolver
    mode: SchemaMode
    name: str | None = None


@dataclass
class LibraryResult:
    """The schemas a resolver generated for its requests.

    ``roots`` maps each request to the key of its schema in ``defs``. ``defs`` are JSON schemas whose references
    use ``#/$defs/<key>`` or tokens returned by :meth:`LibraryRun.embed`. ``names`` maps keys of ``defs`` to
    explicit component names. A schema generated for both modes is keyed ``<key>-Input`` and ``<key>-Output``;
    pairs that turn out identical once all resolvers ran become one component. ``warnings`` are emitted once the
    document is built, from the resolver's last result only.
    """

    roots: dict[LibraryRequest, str]
    defs: dict[str, dict[str, Any]]
    names: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


class LibraryRun:
    """What a resolver may use during one resolution round."""

    __slots__ = ("_context", "_embedded")

    def __init__(self, context: "OpenAPIContext", embedded: dict[bytes, tuple[int, "Schema | Reference"]]) -> None:
        self._context = context
        self._embedded = embedded

    def schema_creator(self, mode: SchemaMode) -> "SchemaCreator":
        """Create a schema creator for the types a library hands back to Litestar.

        Args:
            mode: The schema mode to document the types in.

        Returns:
            A schema creator of the document being built, which does not generate examples.
        """
        from litestar._openapi.schema_generation.schema import SchemaCreator

        return SchemaCreator.from_openapi_context(
            self._context, prefer_alias=mode == "validation", schema_mode=mode, generate_examples=False
        )

    @property
    def serializer(self) -> "Serializer":
        """The serializer of the application's type encoders, for encoding defaults and examples."""
        return get_serializer(self._context.type_encoders)

    @property
    def init_plugins(self) -> "Sequence[InitPluginProtocol]":
        """The application's init plugins, in the order they configured it."""
        return self._context.init_plugins

    def embed(self, value: "Schema | Reference") -> dict[str, str]:
        """Turn a Litestar schema into a reference a JSON schema can hold.

        Equal schemas get the same reference.

        Args:
            value: The schema or reference to embed.

        Returns:
            A ``{"$ref": ...}`` JSON schema that becomes ``value`` in the document.
        """
        key = msgspec.json.encode(_tagged(value.to_schema()))
        index, _ = self._embedded.setdefault(key, (len(self._embedded), value))
        return {"$ref": f"{EMBED_PREFIX}{index}"}


def _tagged(value: Any) -> Any:
    kind = type(value)
    if value is None or kind in (str, int, bool) or (kind is float and math.isfinite(value)):
        return value
    if kind in (list, tuple):
        return [kind.__name__, *map(_tagged, value)]
    if kind is dict:
        return ["dict", sorted([_encoded(key), _tagged(item)] for key, item in value.items())]
    if kind in (set, frozenset):
        return [kind.__name__, sorted(map(_encoded, value))]
    return ["object", f"{kind.__module__}.{kind.__qualname__}", repr(value)]


def _encoded(value: Any) -> str:
    return msgspec.json.encode(_tagged(value)).decode()


class MsgspecRoutedPlugin(OpenAPISchemaPlugin):
    """A built-in schema plugin that defers the types msgspec can decode to msgspec.

    Subclasses implement ``_own_schema`` for the types msgspec cannot decode or the schema creator does not defer. A
    subclass that overrides ``to_openapi_schema`` documents every type itself.
    """

    def to_openapi_schema(
        self, field_definition: FieldDefinition, schema_creator: "SchemaCreator"
    ) -> "Schema | Reference":
        """Given a type annotation, transform it into an OpenAPI schema class.

        Args:
            field_definition: FieldDefinition instance.
            schema_creator: An instance of the schema creator class

        Returns:
            An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
        """
        if (placeholder := msgspec_placeholder(self, field_definition, schema_creator)) is not None:
            return placeholder
        return self._own_schema(field_definition, schema_creator)

    @abstractmethod
    def _own_schema(self, field_definition: FieldDefinition, schema_creator: "SchemaCreator") -> "Schema | Reference":
        """Document ``field_definition`` without deferring it to msgspec."""


def routed_to_msgspec(plugin: OpenAPISchemaPlugin) -> TypeGuard[MsgspecRoutedPlugin]:
    return (
        isinstance(plugin, MsgspecRoutedPlugin)
        and type(plugin).to_openapi_schema is MsgspecRoutedPlugin.to_openapi_schema
    )


def msgspec_placeholder(
    plugin: OpenAPISchemaPlugin, field_definition: FieldDefinition, creator: "SchemaCreator"
) -> "Reference | None":
    """Defer ``field_definition`` to msgspec if ``plugin`` routes it there.

    A built-in dataclass, ``Struct``, ``TypedDict`` or attrs plugin routes a type msgspec can decode, unless its
    subclass overrides ``to_openapi_schema`` or ``creator`` documents DTO transfer models.

    Args:
        plugin: The schema plugin that claims ``field_definition``.
        field_definition: The field definition to document.
        creator: The schema creator documenting it.

    Returns:
        A placeholder, or ``None`` if ``plugin`` documents ``field_definition`` itself.
    """
    if creator.library_models and routed_to_msgspec(plugin):
        from litestar._openapi.schema_generation.library._msgspec import MSGSPEC_RESOLVER, supports_msgspec_schema

        if supports_msgspec_schema(field_definition.annotation):
            return creator.for_library(field_definition, MSGSPEC_RESOLVER)
    return None


def claimed_by_other_plugin(creator: "SchemaCreator", annotation: Any, *own: Callable[..., Any]) -> bool:
    """Tell whether a schema plugin other than the resolver's own documents ``annotation``.

    The built-in plugins that defer types to msgspec do not count as other plugins.

    Args:
        creator: The schema creator whose plugins to look up.
        annotation: The type to look up.
        *own: The ``to_openapi_schema`` functions of the plugins that defer to the resolver.

    Returns:
        Whether another schema plugin documents ``annotation``, so the resolver embeds its Litestar schema.
    """
    plugin = creator.get_plugin_for(FieldDefinition.from_annotation(annotation))
    return plugin is not None and type(plugin).to_openapi_schema not in {*own, MsgspecRoutedPlugin.to_openapi_schema}


def kwarg_definition_metadata(metadata: Iterable[Any], serializer: "Serializer") -> dict[str, Any]:
    """Return the title, description and example values of the first ``KwargDefinition`` in ``metadata``.

    Examples are encoded with ``serializer`` and left out if it cannot encode them.
    """
    definition = next((item for item in metadata if isinstance(item, KwargDefinition)), None)
    if definition is None:
        return {}
    result: dict[str, Any] = {key: value for key in ("title", "description") if (value := getattr(definition, key))}
    if definition.examples:
        with suppress(TypeError, ValueError, msgspec.MsgspecError):
            result["examples"] = msgspec.json.decode(
                msgspec.json.encode([example.value for example in definition.examples], enc_hook=serializer)
            )
    return result


def map_references(node: Any, replace: Callable[[str], Any], markers: Sequence[str] = ()) -> Any:
    """Copy a JSON schema with each reference passed through ``replace``.

    References are ``$ref`` values and discriminator mapping targets. A discriminator whose mapping has a target
    that is not a string is dropped.

    Args:
        node: The JSON schema, or a value in it.
        replace: Maps a reference to its replacement.
        markers: Keys whose value is a reference that replaces ``$ref``; the first one present wins.

    Returns:
        The copy, with each marker key removed.
    """
    if isinstance(node, list):
        return [map_references(item, replace, markers) for item in node]
    if not isinstance(node, dict):
        return node
    result = {key: map_references(value, replace, markers) for key, value in node.items() if key not in markers}
    if isinstance(ref := next((node[key] for key in (*markers, "$ref") if key in node), None), str):
        result["$ref"] = replace(ref)
    if isinstance(discriminator := node.get("discriminator"), dict) and isinstance(
        mapping := discriminator.get("mapping"), dict
    ):
        if all(isinstance(target, str) for target in mapping.values()):
            result["discriminator"] = {
                **discriminator,
                "mapping": {key: replace(target) for key, target in mapping.items()},
            }
        else:
            del result["discriminator"]
    return result


def renamer(names: Mapping[str, str]) -> Callable[[str], str]:
    targets = {f"{LOCAL_PREFIX}{key}": f"{LOCAL_PREFIX}{target}" for key, target in names.items()}
    return lambda ref: targets.get(ref, ref)


def _references(node: Any) -> Iterator[str]:
    if isinstance(node, list):
        for item in node:
            yield from _references(item)
    elif isinstance(node, dict):
        for key, item in node.items():
            if key == "$ref" and isinstance(item, str):
                yield item
            elif key == "discriminator" and isinstance(item, dict) and isinstance(item.get("mapping"), dict):
                yield from (target for target in item["mapping"].values() if isinstance(target, str))
            else:
                yield from _references(item)


def local_name(ref: str) -> str | None:
    return ref[len(LOCAL_PREFIX) :] if ref.startswith(LOCAL_PREFIX) else None


def embed_index(ref: str) -> int | None:
    index = ref[len(EMBED_PREFIX) :]
    return int(index) if ref.startswith(EMBED_PREFIX) and index.isdigit() else None


def local_references(node: Any) -> Iterator[str]:
    return (name for ref in _references(node) if (name := local_name(ref)) is not None)


def reachable(roots: Iterable[str], defs: Mapping[str, Any]) -> dict[str, None]:
    """Find the defs that local references reach from ``roots``.

    Args:
        roots: The def keys to start from; each must be in ``defs``.
        defs: The JSON schemas by def key.

    Returns:
        The def keys reached, in discovery order; a root is included only if a reference reaches it.
    """
    found: dict[str, None] = {}
    stack = list(roots)
    while stack:
        for name in local_references(defs[stack.pop()]):
            if name in defs and name not in found:
                found[name] = None
                stack.append(name)
    return found


def unique_names(candidates: Mapping[_K, tuple[str, str]]) -> dict[_K, str]:
    """Give each key a distinct name made of component key characters.

    A key takes its short name unless another key shares it, then its qualified name. Remaining clashes get the
    first free ``_<n>`` suffix from 2, in the order of ``candidates``.

    Args:
        candidates: The short and qualified name of each key, in priority order.

    Returns:
        The name of each key.
    """
    sanitised = {
        key: (INVALID_KEY_CHARACTER_PATTERN.sub("_", short), INVALID_KEY_CHARACTER_PATTERN.sub("_", qualified))
        for key, (short, qualified) in candidates.items()
    }
    counts = Counter(short for short, _ in sanitised.values())
    preferred = {key: short if counts[short] == 1 else qualified for key, (short, qualified) in sanitised.items()}
    taken = set(preferred.values())
    names: dict[_K, str] = {}
    used: set[str] = set()
    for key, name in preferred.items():
        names[key] = candidate = unique_name_for_scope(name, taken, start=2) if name in used else name
        used.add(candidate)
        taken.add(candidate)
    return names


def build_result(
    roots: Mapping[LibraryRequest, str],
    defs: Mapping[SchemaMode, Mapping[str, dict[str, Any]]],
    candidates: Mapping[str, tuple[str, str]],
    explicit: Mapping[str, str],
    warnings: Iterable[str] = (),
    identities: Mapping[str, tuple[str, SchemaMode]] | None = None,
) -> LibraryResult:
    """Name the schemas a resolver generated per def key and mode.

    A def key generated in both modes gets ``-Input`` and ``-Output`` keys. A def key keeps its short name unless
    another documented def key shares it, then its qualified name; a def key with an explicit name always uses its
    qualified name and carries the explicit one in :attr:`LibraryResult.names`. Remaining clashes get a numeric
    suffix, given in the order of ``candidates``.

    Args:
        roots: The reference key of each request's schema.
        defs: The schemas generated in each mode, by def key. They refer to each other with
            ``#/$defs/<reference key>``.
        candidates: The short and qualified name of each def key, in priority order; may include def keys without
            schemas.
        explicit: The explicit component name of def keys.
        warnings: Warnings to emit once the document is built.
        identities: The def key and mode each reference key points at. Without it, a reference key is the def key
            it points at in the mode of the request or schema that uses it.

    Returns:
        The resolver result.

    Raises:
        SchemaConversionError: If a root reference key points at no schema.
    """
    both = set(defs.get("validation", {})) & set(defs.get("serialization", {}))
    documented = {def_key for mode_defs in defs.values() for def_key in mode_defs}
    final = unique_names(
        {
            def_key: (qualified, qualified) if def_key in explicit else (short, qualified)
            for def_key, (short, qualified) in candidates.items()
            if def_key in documented
        }
    )
    keys = {
        mode: {def_key: f"{final[def_key]}{suffix if def_key in both else ''}" for def_key in defs[mode]}
        for mode, suffix in MODES
        if mode in defs
    }
    shared = (
        None
        if identities is None
        else {ref_key: keys[mode][def_key] for ref_key, (def_key, mode) in identities.items()}
    )
    targets = {mode: keys.get(mode, {}) if shared is None else shared for mode, _ in MODES}
    result_defs: dict[str, dict[str, Any]] = {}
    names: dict[str, str] = {}
    for mode, suffix in MODES:
        rename = renamer(targets[mode])
        for def_key, result_key in keys.get(mode, {}).items():
            result_defs[result_key] = map_references(defs[mode][def_key], rename)
            if def_key in explicit:
                names[result_key] = f"{explicit[def_key]}{suffix if def_key in both else ''}"
    if missing := [request for request, ref_key in roots.items() if ref_key not in targets[request.mode]]:
        raise SchemaConversionError(
            f"The {missing[0].resolver.name} schema resolver cannot document {missing[0].annotation!r} as a component"
        )
    return LibraryResult(
        roots={request: targets[request.mode][ref_key] for request, ref_key in roots.items()},
        defs=result_defs,
        names=names,
        warnings=tuple(warnings),
    )
