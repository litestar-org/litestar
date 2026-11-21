import sys
import threading
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from litestar._openapi.datastructures import OpenAPIContext, SchemaRegistry, get_component_key_override
from litestar._openapi.schema_generation.library import (
    LibraryRequest,
    LibraryResolver,
    LibraryRun,
    SchemaMode,
    embed_index,
    map_references,
)
from litestar._openapi.schema_generation.library.converter import json_schema_to_spec
from litestar._openapi.schema_generation.library.exceptions import (
    LibrarySchemaError,
    SchemaConversionError,
    UnresolvedSchemaError,
)
from litestar._openapi.schema_generation.library.graph import (
    ResolvedSchemas,
    SchemaKey,
    SchemaNode,
    collapse_merged,
    merge_identical_modes,
    reachable,
)
from litestar._openapi.schema_generation.library.naming import Names, name_components
from litestar.exceptions import LitestarWarning
from litestar.openapi.spec.base import BaseSchemaObject
from litestar.openapi.spec.reference import Reference
from litestar.openapi.spec.schema import Schema
from litestar.serialization.msgspec_hooks import get_serializer
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar._openapi.schema_generation.schema import SchemaCreator

__all__ = ("FrozenLibrarySchemas", "LibraryComponents")

_PLACEHOLDER_PREFIX = "#/components/schemas/litestar-library-"
_COMPONENT_PREFIX = "#/components/schemas/"
_MAX_ROUNDS = 1000
_RECURSION_LIMIT = 10_000
_SCALARS = (str, int, float, bool, type(None))


class _RaisedRecursionLimit:
    """Raise the recursion limit to at least ``_RECURSION_LIMIT`` while any thread is inside the block.

    The first thread to enter saves the limit and the last one to leave restores it.
    """

    __slots__ = ("_active", "_lock", "_saved")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0
        self._saved = 0

    def __enter__(self) -> None:
        with self._lock:
            if not self._active:
                self._saved = sys.getrecursionlimit()
                sys.setrecursionlimit(max(self._saved, _RECURSION_LIMIT))
            self._active += 1

    def __exit__(self, *exc_info: object) -> None:
        with self._lock:
            self._active -= 1
            if not self._active:
                sys.setrecursionlimit(self._saved)


_RAISED_RECURSION_LIMIT = _RaisedRecursionLimit()


@dataclass(frozen=True, slots=True)
class FrozenLibrarySchemas:
    """The library-generated components of one OpenAPI document.

    ``components`` are the new components by name, in which no placeholder is left; ``targets`` maps each
    placeholder to the path of its component.
    """

    components: Mapping[str, Schema]
    targets: Mapping[str, str]


class LibraryComponents:
    """The library-generated schemas of one OpenAPI document.

    Schema plugins get a placeholder for each type they defer to a library resolver. Once every path is documented,
    :meth:`resolve` runs the resolvers, :meth:`freeze` turns their schemas into components and
    :meth:`point_references` points the placeholders at those components.
    """

    __slots__ = (
        "_embedded",
        "_example_resolvers",
        "_frozen",
        "_requests",
        "_resolvers",
        "_results",
        "_tokens",
    )

    def __init__(self) -> None:
        self._requests: dict[LibraryRequest, str] = {}
        self._tokens: dict[str, LibraryRequest] = {}
        self._frozen: FrozenLibrarySchemas | None = None
        self._resolvers: dict[str, LibraryResolver] = {}
        self._results: dict[str, ResolvedSchemas] = {}
        self._embedded: dict[bytes, tuple[int, Schema | Reference]] = {}
        self._example_resolvers: dict[Any, LibraryResolver | None] = {}

    def placeholder(self, field_definition: FieldDefinition, resolver: LibraryResolver, mode: SchemaMode) -> Reference:
        """Request the schema of a type from a library resolver.

        Args:
            field_definition: The field definition to document; its ``schema_component_key`` is the explicit
                component name.
            resolver: The resolver to document the type with.
            mode: The schema mode to document the type in.

        Returns:
            A placeholder, the same for equal requests, that :meth:`point_references` points at the component.

        Raises:
            LibrarySchemaError: If the components are already frozen, or another resolver of the same name is in use.
        """
        if self._frozen is not None:
            raise LibrarySchemaError(
                "Cannot request a library-generated schema once the components of the document are generated"
            )
        if self._resolvers.setdefault(resolver.name, resolver) is not resolver:
            raise LibrarySchemaError(
                f"Two schema resolvers are named {resolver.name!r}: {self._resolvers[resolver.name]!r} and {resolver!r}"
            )
        request = LibraryRequest(
            field_definition.annotation, resolver, mode, get_component_key_override(field_definition)
        )
        if (token := self._requests.get(request)) is None:
            token = self._requests[request] = f"{_PLACEHOLDER_PREFIX}{len(self._requests)}"
            self._tokens[token] = request
        return Reference(token)

    def is_placeholder(self, reference: Reference) -> bool:
        """Tell whether a reference is a placeholder of these components.

        Args:
            reference: The reference to check.

        Returns:
            Whether ``reference`` has the target of a placeholder :meth:`placeholder` returned.
        """
        return reference.ref in self._tokens

    def to_input_example(self, creator: "SchemaCreator", value: Any) -> Any:
        """Convert a value in a generated input example to a value validation accepts.

        A model instance is converted by the library resolver that documents its type, any other value by the
        application's serializer.

        Args:
            creator: The schema creator generating the example.
            value: The value to convert.

        Returns:
            A value validation accepts.

        Raises:
            TypeError: If neither can convert ``value``.
            ValueError: If no JSON dump of ``value`` passes validation.
        """
        if (cls := type(value)) not in self._example_resolvers:
            self._example_resolvers[cls] = self._claiming_resolver(creator, cls)
        if (resolver := self._example_resolvers[cls]) is None:
            return get_serializer(creator.type_encoders)(value)
        return resolver.to_input_example(value)

    @staticmethod
    def _claiming_resolver(creator: "SchemaCreator", cls: Any) -> LibraryResolver | None:
        field_definition = FieldDefinition.from_annotation(cls)
        probe = creator.replace(schema_registry=SchemaRegistry(), generate_examples=False)
        try:
            plugin = creator.get_plugin_for(field_definition)
            placeholder = None if plugin is None else plugin.to_openapi_schema(field_definition, probe)
        except Exception:  # noqa: BLE001
            return None
        if (
            not isinstance(placeholder, Reference)
            or (request := probe.schema_registry.library._tokens.get(placeholder.ref)) is None
        ):
            return None
        return request.resolver

    def resolve(self, context: OpenAPIContext) -> None:
        """Run the resolvers until every request has a schema.

        Resolving can add requests: a resolver hands types back to Litestar, which may defer them to a library again.
        Each round runs, in name order, every resolver whose last result does not cover all of its requests, passing
        all of them.

        Resolvers run with the recursion limit raised to at least 10000, so how deeply models may nest depends on the
        interpreter's C recursion limit instead: about 990 nested msgspec models on Python 3.13, and only about a
        hundred on Python 3.12.

        Args:
            context: The context of the document being built.

        Raises:
            UnresolvedSchemaError: If a resolver exceeds the recursion limit or the requests do not settle within
                1000 rounds.
        """
        run = LibraryRun(context, self._embedded)
        for _ in range(_MAX_ROUNDS):
            if not self._unsettled():
                return
            for resolver_name in sorted(self._resolvers):
                requests = [request for request in self._requests if request.resolver.name == resolver_name]
                if (result := self._results.get(resolver_name)) is None or any(
                    request not in result.roots for request in requests
                ):
                    self._resolve(self._resolvers[resolver_name], requests, run)
        if unsettled := self._unsettled():
            raise UnresolvedSchemaError(
                f"Library-generated schemas did not settle after {_MAX_ROUNDS} resolution rounds: every round gave "
                f"the {', '.join(sorted({request.resolver.name for request in unsettled}))} schema resolver new types "
                f"to document, most recently {[request.annotation for request in unsettled]!r}"
            )

    def _unsettled(self) -> list[LibraryRequest]:
        return [
            request
            for request in self._requests
            if (result := self._results.get(request.resolver.name)) is None or request not in result.roots
        ]

    def _resolve(self, resolver: LibraryResolver, requests: list[LibraryRequest], run: LibraryRun) -> None:
        try:
            with _RAISED_RECURSION_LIMIT:
                result = resolver.resolve(requests, run)
        except RecursionError as exc:
            raise UnresolvedSchemaError(
                f"The {resolver.name} schema resolver exceeded the maximum recursion depth"
            ) from exc
        if missing := [request for request in requests if result.roots.get(request) not in result.nodes]:
            raise SchemaConversionError(
                f"The {missing[0].resolver.name} schema resolver cannot document {missing[0].annotation!r} as a "
                "component"
            )
        if len(result.roots) != len(requests):
            raise LibrarySchemaError(
                f"The {resolver.name} schema resolver returned schemas for requests it was not given: "
                f"{[request.annotation for request in result.roots if request not in requests]!r}"
            )
        if foreign := [key for key in result.nodes if key.resolver != resolver.name]:
            raise LibrarySchemaError(
                f"The {resolver.name} schema resolver returned a schema keyed for another resolver: {foreign[0]!r}"
            )
        self._results[resolver.name] = result

    def freeze(self, existing: Mapping[str, Schema]) -> FrozenLibrarySchemas:
        """Convert the resolved schemas to components and record the component of every placeholder.

        Runs in steps: check that every request is resolved, merge the mode pairs whose schemas are identical
        (:func:`~.graph.merge_identical_modes`) into one schema each (:func:`~.graph.collapse_merged`), find the schemas
        reachable from a request (:func:`~.graph.reachable`), name them (:func:`~.naming.name_components`), convert them,
        replace each that got a numeric suffix by an equal existing component, point the placeholders they hold at
        their components, then emit the warnings. Must run after :meth:`resolve`; :meth:`point_references` then points
        the placeholders of the rest of the document. Runs once: later calls return the same result and no new
        placeholder may be requested.

        Args:
            existing: The components Litestar generated for the document; only the first call reads them.

        Returns:
            The new components, keyed by name, none of them in ``existing``, and the target of each placeholder.

        Raises:
            UnresolvedSchemaError: If a request is not resolved.
            SchemaNameConflictError: If an explicit name is taken.
            SchemaConversionError: If a schema cannot be converted.
        """
        if self._frozen is not None:
            return self._frozen
        results = self._settled_results()
        embedded = [value for _, value in self._embedded.values()]
        placeholder_keys = {
            token: results[request.resolver.name].roots[request] for request, token in self._requests.items()
        }
        merged = merge_identical_modes(_nodes(results), embedded, placeholder_keys)
        collapsed = {resolver_name: collapse_merged(result, merged) for resolver_name, result in results.items()}
        nodes = _nodes(collapsed)
        reached = reachable((key for result in collapsed.values() for key in result.roots.values()), nodes)
        names = name_components(collapsed, list(self._requests), reached, existing)
        schemas, targets, dropped = self._fold_into_existing(names, nodes, embedded, existing)
        _point(schemas, targets)
        _warn(dropped, results)
        self._frozen = FrozenLibrarySchemas(MappingProxyType(schemas), MappingProxyType(targets))
        return self._frozen

    def _settled_results(self) -> dict[str, ResolvedSchemas]:
        if unsettled := self._unsettled():
            raise UnresolvedSchemaError(
                f"The library-generated schemas of {[request.annotation for request in unsettled]!r} were never "
                "resolved; a SchemaCreator documents them only within the OpenAPI document of an application"
            )
        return {resolver_name: self._results[resolver_name] for resolver_name in sorted(self._results)}

    def _fold_into_existing(
        self,
        names: Names,
        nodes: Mapping[SchemaKey, SchemaNode],
        embedded: Sequence[Schema | Reference],
        existing: Mapping[str, Schema],
    ) -> tuple[dict[str, Schema], dict[str, str], dict[tuple[str, str], None]]:
        """Convert the named schemas, replacing each that got a numeric suffix by an equal existing component.

        Repeats until no schema is replaced, since a replacement changes the schemas that refer to it.

        Args:
            names: The component names.
            nodes: The nodes by key, with merged pairs collapsed.
            embedded: The embedded Litestar schemas, by index.
            existing: The components Litestar generated for the document.

        Returns:
            The new components by name, the target of each placeholder, and the JSON schema keys left out, with
            their model.
        """
        dropped: dict[tuple[str, str], None] = {}

        def point(ref: str) -> str:
            return targets.get(ref, ref)

        while True:
            targets = {
                token: f"{_COMPONENT_PREFIX}{names.component_of_request[request]}"
                for request, token in self._requests.items()
            }
            schemas = {name: _convert(nodes[key], name, names, embedded, dropped) for name, key in names.keys.items()}
            folds = {
                name: base
                for name in names.keys
                if (base := names.bases[name]) != name
                and base in existing
                and map_references(schemas[name].to_schema(), point)
                == map_references(existing[base].to_schema(), point)
            }
            if not folds:
                return schemas, targets, dropped
            names = names.folded(folds)

    def point_references(self, node: Any) -> None:
        """Point every placeholder reachable from ``node`` at its component, including copies of placeholders.

        Walks the OpenAPI objects, lists, tuples and dicts in ``node`` once. Does nothing before :meth:`freeze`.

        Args:
            node: The OpenAPI object, or a value in it, whose placeholders to point; changed in place.
        """
        if self._frozen is not None:
            _point(node, self._frozen.targets)


def _point(node: Any, targets: Mapping[str, str]) -> None:
    if not targets:
        return
    seen: set[int] = set()
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, Reference):
            item.ref = targets.get(item.ref, item.ref)
        elif isinstance(item, (BaseSchemaObject, list, tuple, dict)) and id(item) not in seen:
            seen.add(id(item))
            values = (
                vars(item).values()
                if isinstance(item, BaseSchemaObject)
                else item.values()
                if isinstance(item, dict)
                else item
            )
            stack.extend(value for value in values if not isinstance(value, _SCALARS))


def _nodes(results: Mapping[str, ResolvedSchemas]) -> dict[SchemaKey, SchemaNode]:
    return {key: node for result in results.values() for key, node in result.nodes.items()}


def _convert(
    node: SchemaNode,
    name: str,
    names: Names,
    embedded: Sequence[Schema | Reference],
    dropped: dict[tuple[str, str], None],
) -> Schema:
    def lookup_ref(ref: str) -> Schema | Reference:
        if (key := node.references.get(ref)) is not None and key in names.component_of:
            return Reference(f"{_COMPONENT_PREFIX}{names.component_of[key]}")
        if (position := embed_index(ref)) is not None and position < len(embedded):
            return embedded[position]
        raise SchemaConversionError(f"Cannot resolve {ref!r} in a library-generated schema")

    keys: set[str] = set()
    schema = json_schema_to_spec(node.schema, lookup_ref, keys)
    dropped.update(((names.models[name], key), None) for key in sorted(keys))
    if isinstance(schema, Reference):
        raise SchemaConversionError(f"The library-generated schema {name!r} is a bare reference")
    return schema


def _warn(dropped: Mapping[tuple[str, str], None], results: Mapping[str, ResolvedSchemas]) -> None:
    for model, key in dropped:
        warnings.warn(
            f"The JSON schema key {key!r} of {model!r} cannot be represented in the OpenAPI document and is dropped",
            category=LitestarWarning,
            stacklevel=1,
        )
    for result in results.values():
        for message in result.warnings:
            warnings.warn(message, category=LitestarWarning, stacklevel=1)
