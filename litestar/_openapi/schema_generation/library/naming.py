from collections import Counter
from collections.abc import Callable, Collection, Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from litestar._openapi.datastructures import INVALID_KEY_CHARACTER_PATTERN
from litestar._openapi.schema_generation.library import (
    LOCAL_PREFIX,
    MODES,
    LibraryRequest,
    SchemaMode,
    map_references,
)
from litestar._openapi.schema_generation.library.exceptions import SchemaNameConflictError
from litestar._openapi.schema_generation.library.graph import NameCandidates, ResolvedSchemas, SchemaKey, SchemaNode
from litestar.utils.helpers import unique_name_for_scope

__all__ = ("Names", "name_components")

_SUFFIX_OF: dict[SchemaMode, str] = dict(MODES)
_Use = tuple[SchemaKey, str | None]


@dataclass(frozen=True, slots=True)
class Names:
    """The component names of the library-generated schemas of one document.

    ``component_of`` names the component of each emitted schema, ``component_of_request`` the component of each
    request. ``keys`` maps each new component to the schema it holds, ``bases`` to the name it was derived from and
    ``models`` to the name of the model it documents, without the suffix of its mode.
    """

    component_of: Mapping[SchemaKey, str]
    component_of_request: Mapping[LibraryRequest, str]
    keys: Mapping[str, SchemaKey]
    bases: Mapping[str, str]
    models: Mapping[str, str]

    def folded(self, into: Mapping[str, str]) -> "Names":
        """Replace new components by existing ones.

        Args:
            into: The existing component that replaces each new one.

        Returns:
            The names, with each replaced component renamed and no longer new.
        """
        return Names(
            component_of={key: into.get(name, name) for key, name in self.component_of.items()},
            component_of_request={request: into.get(name, name) for request, name in self.component_of_request.items()},
            keys={name: key for name, key in self.keys.items() if name not in into},
            bases={name: base for name, base in self.bases.items() if name not in into},
            models={name: model for name, model in self.models.items() if name not in into},
        )


def _sanitised(name: str) -> str:
    return INVALID_KEY_CHARACTER_PATTERN.sub("_", name)


def _unique_names(candidates: Mapping[Hashable, NameCandidates]) -> dict[Hashable, str]:
    sanitised = {
        identity: (
            _sanitised(names.qualified if names.explicit is not None else names.short),
            _sanitised(names.qualified),
        )
        for identity, names in candidates.items()
    }
    counts = Counter(short for short, _ in sanitised.values())
    preferred = {
        identity: short if counts[short] == 1 else qualified for identity, (short, qualified) in sanitised.items()
    }
    taken = set(preferred.values())
    names: dict[Hashable, str] = {}
    used: set[str] = set()
    for identity, name in preferred.items():
        names[identity] = candidate = unique_name_for_scope(name, taken, start=2) if name in used else name
        used.add(candidate)
        taken.add(candidate)
    return names


def _schema_names(
    nodes: Mapping[SchemaKey, SchemaNode],
) -> tuple[dict[SchemaKey, str], dict[SchemaKey, str], dict[SchemaKey, str]]:
    candidates: dict[Hashable, NameCandidates] = {}
    keys_per_identity: Counter[Hashable] = Counter()
    for key, node in nodes.items():
        candidates.setdefault(key.identity, node.names)
        keys_per_identity[key.identity] += 1
    unique = _unique_names(candidates)
    names: dict[SchemaKey, str] = {}
    explicit: dict[SchemaKey, str] = {}
    suffixes: dict[SchemaKey, str] = {}
    for key in nodes:
        suffix = suffixes[key] = _SUFFIX_OF[key.mode] if keys_per_identity[key.identity] > 1 else ""
        names[key] = f"{unique[key.identity]}{suffix}"
        if (name := candidates[key.identity].explicit) is not None:
            explicit[key] = f"{name}{suffix}"
    return names, explicit, suffixes


def _naming_order(
    resolved: Mapping[str, ResolvedSchemas],
    requests: Sequence[LibraryRequest],
    names: Mapping[SchemaKey, str],
    suffixes: Mapping[SchemaKey, str],
) -> tuple[dict[LibraryRequest, _Use], list[_Use]]:
    order = {request: position for position, request in enumerate(requests)}
    root_entries: dict[LibraryRequest, _Use] = {}
    ordered: list[_Use] = []
    for result in resolved.values():
        copies: dict[_Use, None] = {}
        modes: dict[str | None, set[SchemaMode]] = {}
        for request in result.roots:
            modes.setdefault(request.name, set()).add(request.mode)
        for request in sorted(result.roots, key=order.__getitem__):
            key = result.roots[request]
            name = request.name
            if name is not None and len(modes[name]) > 1:
                name += suffixes[key]
            entry = (key, name)
            root_entries.setdefault(request, entry)
            if request.name is not None:
                copies[entry] = None
        ordered.extend(copies)
        ordered.extend((key, None) for key in sorted(result.nodes, key=names.__getitem__))
    return root_entries, ordered


def _comparable(nodes: Mapping[SchemaKey, SchemaNode], names: Mapping[SchemaKey, str]) -> Callable[[SchemaKey], Any]:
    cache: dict[SchemaKey, Any] = {}

    def comparable(key: SchemaKey) -> Any:
        if key not in cache:
            references = nodes[key].references

            def rename(ref: str) -> str:
                if (target := references.get(ref)) is not None and target in names:
                    return f"{LOCAL_PREFIX}{names[target]}"
                return ref

            cache[key] = map_references(nodes[key].schema, rename)
        return cache[key]

    return comparable


def name_components(
    resolved: Mapping[str, ResolvedSchemas],
    requests: Sequence[LibraryRequest],
    reached: Collection[SchemaKey],
    existing: Collection[str],
) -> Names:
    """Name the components of the emitted library-generated schemas.

    Per resolver, a schema takes the short name of its identity unless another identity of the resolver shares it,
    then its qualified name; an identity with an explicit name uses its qualified name. Remaining clashes get the
    first free ``_<n>`` suffix from 2, in ``nodes`` order. An identity documented in both modes gets ``-Input`` and
    ``-Output``.

    A request with an explicit name gets a component of that name, suffixed when the name is requested in both
    modes. Explicitly named schemas are named first, then the others in name order; equal schemas of one resolver
    under one base name share a component, and a base name already taken gets the first free ``_<n>`` suffix from 2.

    Args:
        resolved: The schemas of each resolver, in resolver name order, with merged pairs collapsed.
        requests: Every request, in request order.
        reached: The keys references reach from the roots of the requests.
        existing: Component names already used in the document.

    Returns:
        The component names.

    Raises:
        SchemaNameConflictError: If an explicit name is taken by a different schema.
    """
    nodes = {key: node for result in resolved.values() for key, node in result.nodes.items()}
    names: dict[SchemaKey, str] = {}
    explicit: dict[SchemaKey, str] = {}
    suffixes: dict[SchemaKey, str] = {}
    for result in resolved.values():
        resolver_names, resolver_explicit, resolver_suffixes = _schema_names(result.nodes)
        names.update(resolver_names)
        explicit.update(resolver_explicit)
        suffixes.update(resolver_suffixes)
    root_entries, ordered = _naming_order(resolved, requests, names, suffixes)
    emitted = {*root_entries.values(), *((key, None) for key in reached)}

    def is_explicit(entry: _Use) -> bool:
        return entry[1] is not None or entry[0] in explicit

    entries = sorted((entry for entry in ordered if entry in emitted), key=lambda entry: not is_explicit(entry))
    comparable = _comparable(nodes, names)
    final: dict[_Use, str] = {}
    components: dict[str, SchemaKey] = {}
    bases: dict[str, str] = {}
    models: dict[str, str] = {}
    taken = set(existing)
    named: dict[tuple[str, str], list[tuple[SchemaKey, str]]] = {}
    for entry in entries:
        key, request_name = entry
        base = _sanitised(explicit.get(key, names[key]) if request_name is None else request_name)
        same = named.setdefault((key.resolver, base), [])
        if shared := next((name for other, name in same if comparable(other) == comparable(key)), None):
            final[entry] = shared
            continue
        if base not in taken:
            name = base
        elif is_explicit(entry):
            raise SchemaNameConflictError(
                f"Schema component keys must be unique. Cannot use the key {base!r} for a library-generated "
                "schema, it is already used by a different schema"
            )
        else:
            name = unique_name_for_scope(base, taken, start=2)
        final[entry] = name
        components[name] = key
        bases[name] = base
        models[name] = name.removesuffix(suffixes[key]) if suffixes[key] else name
        taken.add(name)
        same.append((key, name))
    return Names(
        component_of={key: name for (key, request_name), name in final.items() if request_name is None},
        component_of_request={request: final[entry] for request, entry in root_entries.items()},
        keys=components,
        bases=bases,
        models=models,
    )
