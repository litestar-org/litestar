import math
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeGuard

import msgspec.json

from litestar._openapi.schema_generation.library.converter import EMBED_PREFIX
from litestar.params import KwargDefinition
from litestar.plugins import OpenAPISchemaPlugin
from litestar.serialization.msgspec_hooks import get_serializer
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar._openapi.schema_generation.library.graph import ResolvedSchemas
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
    "LibraryRun",
    "MsgspecRoutedPlugin",
    "SchemaMode",
    "claimed_by_other_plugin",
    "embed_index",
    "kwarg_definition_metadata",
    "map_references",
    "msgspec_placeholder",
    "routed_to_msgspec",
)

SchemaMode = Literal["validation", "serialization"]

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
    def resolve(self, requests: Sequence["LibraryRequest"], run: "LibraryRun") -> "ResolvedSchemas":
        """Generate the schemas of ``requests``, all the requests made with this resolver so far.

        A resolution round runs the resolver again whenever requests were added since its last run.

        Args:
            requests: The schema requests to resolve.
            run: What the resolver may use during this round.

        Returns:
            The generated schemas and their name candidates; the root of every request in ``requests`` must be one of
            the nodes.
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


def embed_index(ref: str) -> int | None:
    index = ref[len(EMBED_PREFIX) :]
    return int(index) if ref.startswith(EMBED_PREFIX) and index.isdigit() else None
