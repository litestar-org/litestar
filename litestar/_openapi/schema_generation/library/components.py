import sys
import threading
import warnings
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, fields
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, NamedTuple

from litestar._openapi.datastructures import (
    INVALID_KEY_CHARACTER_PATTERN,
    OpenAPIContext,
    SchemaRegistry,
    get_component_key_override,
)
from litestar._openapi.schema_generation.library import (
    MODES,
    LibraryRequest,
    LibraryResolver,
    LibraryResult,
    LibraryRun,
    SchemaMode,
    embed_index,
    local_name,
    map_references,
    reachable,
    renamer,
)
from litestar._openapi.schema_generation.library.converter import json_schema_to_spec
from litestar._openapi.schema_generation.library.exceptions import (
    LibrarySchemaError,
    SchemaConversionError,
    SchemaNameConflictError,
    UnresolvedSchemaError,
)
from litestar.exceptions import LitestarWarning
from litestar.openapi.spec.base import BaseSchemaObject
from litestar.openapi.spec.reference import Reference
from litestar.openapi.spec.schema import Schema
from litestar.serialization.msgspec_hooks import get_serializer
from litestar.typing import FieldDefinition
from litestar.utils.helpers import unique_name_for_scope

if TYPE_CHECKING:
    from litestar._openapi.schema_generation.schema import SchemaCreator

__all__ = ("FrozenLibrarySchemas", "LibraryComponents")

_PLACEHOLDER_PREFIX = "#/components/schemas/litestar-library-"
_INPUT, _OUTPUT = (suffix for _, suffix in MODES)
_MAX_ROUNDS = 1000
_RECURSION_LIMIT = 10_000


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


class _Entry(NamedTuple):
    resolver_name: str
    def_key: str
    name: str | None = None


_Results = dict[str, LibraryResult]
_Node = tuple[str, str]


def _suffix(key: str) -> str:
    return next((suffix for suffix in (_INPUT, _OUTPUT) if key.endswith(suffix)), "")


def _base_name(results: _Results, entry: _Entry) -> str:
    name = results[entry.resolver_name].names.get(entry.def_key, entry.def_key) if entry.name is None else entry.name
    return INVALID_KEY_CHARACTER_PATTERN.sub("_", name)


def _is_explicit(results: _Results, entry: _Entry) -> bool:
    return entry.name is not None or entry.def_key in results[entry.resolver_name].names


def _mode_pairs(results: _Results) -> set[_Node]:
    return {
        (resolver_name, stem)
        for resolver_name, result in results.items()
        for def_key in result.defs
        if def_key.endswith(_INPUT)
        and f"{(stem := def_key.removesuffix(_INPUT))}{_OUTPUT}" in result.defs
        and stem not in result.defs
    }


def _propagate_split(split: set[_Node], referenced_pairs: dict[_Node, set[_Node]]) -> set[_Node]:
    grown = bool(split)
    while grown:
        grown = False
        for pair, targets in referenced_pairs.items():
            if pair not in split and not targets.isdisjoint(split):
                split.add(pair)
                grown = True
    return split


def _merged(result: LibraryResult, stems: Collection[str]) -> LibraryResult:
    merged_keys = {f"{stem}{suffix}": stem for stem in stems for suffix in (_INPUT, _OUTPUT)}
    rename = renamer(merged_keys)
    defs = {
        merged_keys.get(def_key, def_key): map_references(definition, rename)
        for def_key, definition in result.defs.items()
        if not (def_key.endswith(_OUTPUT) and def_key in merged_keys)
    }
    names = {
        merged_keys.get(def_key, def_key): name.removesuffix(_INPUT) if def_key in merged_keys else name
        for def_key, name in result.names.items()
        if not (def_key.endswith(_OUTPUT) and def_key in merged_keys)
    }
    roots = {request: merged_keys.get(def_key, def_key) for request, def_key in result.roots.items()}
    return LibraryResult(roots=roots, defs=defs, names=names)


@dataclass(frozen=True, slots=True)
class FrozenLibrarySchemas:
    """The library-generated components of one OpenAPI document.

    ``components`` are the new components by name; ``targets`` maps each placeholder to the path of its component.
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
        self._results: _Results = {}
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
            LibrarySchemaError: If the components are already frozen.
        """
        if self._frozen is not None:
            raise LibrarySchemaError(
                "Cannot request a library-generated schema once the components of the document are generated"
            )
        self._resolvers.setdefault(resolver.name, resolver)
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
        self._results[resolver.name] = result

    def freeze(self, existing: Mapping[str, Schema]) -> FrozenLibrarySchemas:
        """Convert the resolved schemas to components and record the component of every placeholder.

        Only schemas reachable from a request are emitted. Explicitly named schemas are named before the others, and
        identical schemas of one resolver under one name become one component. A schema that got a numeric suffix
        because an existing component already uses its name is replaced by that component if both are equal; this
        repeats until no schema changes, since a replacement changes the schemas that refer to it. Must run after
        :meth:`resolve`; :meth:`point_references` then points the placeholders at their components. Runs once: later
        calls return the same result and no new placeholder may be requested.

        Args:
            existing: The components Litestar generated for the document.

        Returns:
            The new components, keyed by name, none of them in ``existing``, and the target of each placeholder.

        Raises:
            UnresolvedSchemaError: If a request is not resolved.
            SchemaNameConflictError: If an explicit name is taken.
            SchemaConversionError: If a schema cannot be converted.
        """
        if self._frozen is not None:
            return self._frozen
        if unsettled := self._unsettled():
            raise UnresolvedSchemaError(
                f"The library-generated schemas of {[request.annotation for request in unsettled]!r} were never "
                "resolved; a SchemaCreator documents them only within the OpenAPI document of an application"
            )
        embedded = [value for _, value in self._embedded.values()]
        results = self._merge_identical_modes(embedded)
        root_entries, ordered = self._entries(results)
        emitted = set(root_entries.values())
        for entry in list(emitted):
            emitted.update(
                _Entry(entry.resolver_name, def_key)
                for def_key in reachable([entry.def_key], results[entry.resolver_name].defs)
            )
        entries = sorted(
            (entry for entry in ordered if entry in emitted), key=lambda entry: not _is_explicit(results, entry)
        )
        final, components = self._final_names(results, entries, existing)
        dropped: dict[tuple[str, str], None] = {}

        def point(ref: str) -> str:
            return targets.get(ref, ref)

        while True:
            targets = {
                token: f"#/components/schemas/{final[root_entries[request]]}"
                for request, token in self._requests.items()
            }
            schemas = {
                name: self._convert(results, name, entry, final, embedded, dropped)
                for name, entry in components.items()
            }
            merged = {
                name: base
                for name, entry in components.items()
                if (base := _base_name(results, entry)) != name
                and base in existing
                and map_references(schemas[name].to_schema(), point)
                == map_references(existing[base].to_schema(), point)
            }
            if not merged:
                break
            final = {entry: merged.get(name, name) for entry, name in final.items()}
            components = {name: entry for name, entry in components.items() if name not in merged}

        for model, key in dropped:
            warnings.warn(
                f"The JSON schema key {key!r} of {model!r} cannot be represented in the OpenAPI document "
                "and is dropped",
                category=LitestarWarning,
                stacklevel=1,
            )
        for resolver_name in sorted(self._results):
            for message in self._results[resolver_name].warnings:
                warnings.warn(message, category=LitestarWarning, stacklevel=1)
        self._frozen = FrozenLibrarySchemas(MappingProxyType(schemas), MappingProxyType(targets))
        return self._frozen

    def point_references(self, node: Any) -> None:
        """Point every placeholder reachable from ``node`` at its component, including copies of placeholders.

        Walks the OpenAPI objects, lists, tuples and dicts in ``node`` once. Does nothing before :meth:`freeze`.

        Args:
            node: The OpenAPI object, or a value in it, whose placeholders to point; changed in place.
        """
        if self._frozen is None or not (targets := self._frozen.targets):
            return
        seen: set[int] = set()
        stack = [node]
        while stack:
            item = stack.pop()
            if isinstance(item, Reference):
                item.ref = targets.get(item.ref, item.ref)
            elif isinstance(item, (BaseSchemaObject, list, tuple, dict)) and id(item) not in seen:
                seen.add(id(item))
                if isinstance(item, BaseSchemaObject):
                    stack.extend(getattr(item, f.name) for f in fields(item))
                else:
                    stack.extend(item.values() if isinstance(item, dict) else item)

    def _merge_identical_modes(self, embedded: list[Schema | Reference]) -> _Results:
        """Merge each ``-Input``/``-Output`` pair whose schemas turn out identical into one unsuffixed schema.

        Schemas are compared with references to other pairs and embedded Litestar schemas normalised, since those
        targets may themselves be merged. A pair stays split if its schemas differ or it refers to a pair that stays
        split, so a merged schema never refers to a mode-specific one.

        Args:
            embedded: The embedded Litestar schemas, by index.

        Returns:
            The results by resolver name, sorted, with merged pairs renamed in ``defs``, ``names`` and ``roots``.
        """
        results = {resolver_name: self._results[resolver_name] for resolver_name in sorted(self._results)}
        pairs = _mode_pairs(results)
        normalised = self._normaliser(results, pairs, embedded)
        referenced_pairs: dict[_Node, set[_Node]] = {}
        split: set[_Node] = set()
        for resolver_name, stem in pairs:
            (validation, from_validation), (serialization, from_serialization) = (
                normalised(resolver_name, f"{stem}{suffix}") for suffix in (_INPUT, _OUTPUT)
            )
            referenced_pairs[resolver_name, stem] = (from_validation | from_serialization) & pairs
            if validation != serialization:
                split.add((resolver_name, stem))
        merged = pairs - _propagate_split(split, referenced_pairs)
        return {
            resolver_name: _merged(result, stems)
            if (stems := [stem for owner, stem in merged if owner == resolver_name])
            else result
            for resolver_name, result in results.items()
        }

    def _normaliser(
        self, results: _Results, pairs: set[_Node], embedded: list[Schema | Reference]
    ) -> Callable[[str, str], tuple[Any, set[_Node]]]:
        """Build a function that makes a schema comparable across modes.

        The function maps ``(resolver name, def key)`` to the schema with each reference to a pair replaced by the pair's
        node, each other local reference by its own node, and each embedded schema by its normalised content, in
        which placeholders become the node of their schema; it also returns the nodes found. Embedded schemas are
        normalised once.

        Args:
            results: The results by resolver name.
            pairs: The ``(resolver name, stem)`` nodes of the ``-Input``/``-Output`` pairs.
            embedded: The embedded Litestar schemas, by index.

        Returns:
            The normalising function.
        """
        normalised_embeds: dict[int, tuple[Any, set[_Node]]] = {}

        def node(resolver_name: str, def_key: str) -> _Node:
            stem = def_key.removesuffix(_suffix(def_key))
            return (resolver_name, stem) if (resolver_name, stem) in pairs else (resolver_name, def_key)

        def normalised_embed(index: int) -> tuple[Any, set[_Node]]:
            if index not in normalised_embeds:
                found: set[_Node] = set()

                def replace(ref: str) -> Any:
                    if (request := self._tokens.get(ref)) is None:
                        return ref
                    found.add(target := node(request.resolver.name, results[request.resolver.name].roots[request]))
                    return target

                normalised_embeds[index] = (map_references(embedded[index].to_schema(), replace), found)
            return normalised_embeds[index]

        def normalised(resolver_name: str, def_key: str) -> tuple[Any, set[_Node]]:
            found: set[_Node] = set()

            def replace(ref: str) -> Any:
                if (target_key := local_name(ref)) is not None:
                    found.add(target := node(resolver_name, target_key))
                    return target
                if (index := embed_index(ref)) is not None:
                    content, nodes = normalised_embed(index)
                    found.update(nodes)
                    return content
                return ref

            return map_references(results[resolver_name].defs[def_key], replace), found

        return normalised

    def _entries(self, results: _Results) -> tuple[dict[LibraryRequest, _Entry], list[_Entry]]:
        """List the schemas that may become components, in naming order.

        Resolvers follow each other in name order. For each, a request with an explicit component name first gets an
        entry carrying that name, suffixed ``-Input`` or ``-Output`` when the name is requested in both modes, in
        request order; every schema of the resolver follows in def key order.

        Args:
            results: The results by resolver name, sorted.

        Returns:
            The entry of each request, and all entries in naming order.
        """
        order = {request: position for position, request in enumerate(self._requests)}
        root_entries: dict[LibraryRequest, _Entry] = {}
        ordered: list[_Entry] = []
        for resolver_name, result in results.items():
            copies: dict[_Entry, None] = {}
            modes: dict[str | None, set[SchemaMode]] = {}
            for request in result.roots:
                modes.setdefault(request.name, set()).add(request.mode)
            for request in sorted(result.roots, key=order.__getitem__):
                def_key = result.roots[request]
                name = request.name
                if name is not None and len(modes[name]) > 1:
                    name += _suffix(def_key)
                entry = _Entry(resolver_name, def_key, name)
                root_entries.setdefault(request, entry)
                if request.name is not None:
                    copies[entry] = None
            ordered.extend(copies)
            ordered.extend(_Entry(resolver_name, def_key) for def_key in sorted(result.defs))
        return root_entries, ordered

    @staticmethod
    def _final_names(
        results: _Results, entries: list[_Entry], taken_names: Collection[str]
    ) -> tuple[dict[_Entry, str], dict[str, _Entry]]:
        """Give each entry a component name, in order.

        An entry whose schema equals an earlier one of the same resolver and base name shares that component.
        Otherwise it takes its base name if free, or, unless explicit, the base name with the first free ``_<n>``
        suffix from 2.

        Args:
            results: The results by resolver name.
            entries: The entries to name, explicit ones first.
            taken_names: Component names already used in the document.

        Returns:
            The component name of each entry, and the entry behind each new component.

        Raises:
            SchemaNameConflictError: If an explicit name is taken by a different schema.
        """
        final: dict[_Entry, str] = {}
        components: dict[str, _Entry] = {}
        taken = set(taken_names)
        named: dict[tuple[str, str], list[tuple[dict[str, Any], str]]] = {}
        for entry in entries:
            base = _base_name(results, entry)
            definition = results[entry.resolver_name].defs[entry.def_key]
            same = named.setdefault((entry.resolver_name, base), [])
            if shared := next((name for other, name in same if other == definition), None):
                final[entry] = shared
                continue
            if base not in taken:
                name = base
            elif _is_explicit(results, entry):
                raise SchemaNameConflictError(
                    f"Schema component keys must be unique. Cannot use the key {base!r} for a library-generated "
                    "schema, it is already used by a different schema"
                )
            else:
                name = unique_name_for_scope(base, taken, start=2)
            final[entry] = name
            components[name] = entry
            taken.add(name)
            same.append((definition, name))
        return final, components

    @staticmethod
    def _convert(
        results: _Results,
        name: str,
        entry: _Entry,
        final: dict[_Entry, str],
        embedded: list[Schema | Reference],
        dropped: dict[tuple[str, str], None],
    ) -> Schema:
        def lookup_ref(ref: str) -> Schema | Reference:
            if (def_key := local_name(ref)) is not None and (target := _Entry(entry.resolver_name, def_key)) in final:
                return Reference(f"#/components/schemas/{final[target]}")
            if (position := embed_index(ref)) is not None and position < len(embedded):
                return embedded[position]
            raise SchemaConversionError(f"Cannot resolve {ref!r} in a library-generated schema")

        keys: set[str] = set()
        schema = json_schema_to_spec(results[entry.resolver_name].defs[entry.def_key], lookup_ref, keys)
        model = name.removesuffix(_suffix(name))
        dropped.update(((model, key), None) for key in sorted(keys))
        if isinstance(schema, Reference):
            raise SchemaConversionError(f"The library-generated schema {name!r} is a bare reference")
        return schema
