from collections.abc import Callable, Collection, Hashable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar._openapi.schema_generation.library import MODES, LibraryRequest, SchemaMode, embed_index, map_references

if TYPE_CHECKING:
    from litestar.openapi.spec.reference import Reference
    from litestar.openapi.spec.schema import Schema

__all__ = (
    "NameCandidates",
    "ResolvedSchemas",
    "SchemaKey",
    "SchemaNode",
    "collapse_merged",
    "merge_identical_modes",
    "reachable",
    "schema_node",
)

Pair = tuple[str, Hashable]


@dataclass(frozen=True, slots=True)
class SchemaKey:
    """The identity of one schema a resolver generated.

    ``resolver`` is the name of the resolver, ``identity`` tells its schemas apart, and ``mode`` the two schemas of an
    identity documented in both modes.
    """

    resolver: str
    identity: Hashable
    mode: SchemaMode


@dataclass(frozen=True, slots=True)
class NameCandidates:
    """The names a schema may get as a component.

    ``short`` is the name it takes when no other schema of its resolver shares it, ``qualified`` the name it takes
    otherwise, and ``explicit`` the component name its type declares, if any.
    """

    short: str
    qualified: str
    explicit: str | None = None


@dataclass(frozen=True, slots=True)
class SchemaNode:
    """A JSON schema a resolver generated.

    ``references`` maps each local reference in ``schema`` to the key of the schema it points at. References to
    embedded Litestar schemas are tokens returned by :meth:`LibraryRun.embed` and are not in ``references``.
    """

    schema: dict[str, Any]
    references: Mapping[str, SchemaKey]
    names: NameCandidates


@dataclass(frozen=True, slots=True)
class ResolvedSchemas:
    """The schemas a resolver generated for its requests.

    ``roots`` maps each request to the key of its schema in ``nodes``. ``nodes`` iterate in naming priority order,
    the keys of one identity next to each other. An identity documented in both modes has a key per mode; pairs that
    turn out identical once all resolvers ran become one component. ``warnings`` are emitted once the document is
    built, from the resolver's last result only.
    """

    roots: Mapping[LibraryRequest, SchemaKey]
    nodes: Mapping[SchemaKey, SchemaNode]
    warnings: tuple[str, ...] = ()


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


def schema_node(schema: dict[str, Any], targets: Mapping[str, SchemaKey], names: NameCandidates) -> SchemaNode:
    """Build the node of a generated schema.

    Args:
        schema: The JSON schema.
        targets: The key each local reference of the resolver points at.
        names: The name candidates of the schema.

    Returns:
        The node, whose references are those of ``schema`` found in ``targets``.
    """
    references = {ref: key for ref in _references(schema) if (key := targets.get(ref)) is not None}
    return SchemaNode(schema, references, names)


def reachable(roots: Iterable[SchemaKey], nodes: Mapping[SchemaKey, SchemaNode]) -> dict[SchemaKey, None]:
    """Find the nodes that references reach from ``roots``, looking each node up once.

    Args:
        roots: The keys to start from; each must be in ``nodes``.
        nodes: The nodes by key.

    Returns:
        The keys reached, in discovery order; a root is included only if a reference reaches it.
    """
    found: dict[SchemaKey, None] = {}
    expanded: set[SchemaKey] = set()
    stack = list(roots)
    while stack:
        if (key := stack.pop()) in expanded:
            continue
        expanded.add(key)
        for target in nodes[key].references.values():
            if target not in found and target in nodes:
                found[target] = None
                stack.append(target)
    return found


def _normaliser(
    nodes: Mapping[SchemaKey, SchemaNode],
    pairs: Collection[Pair],
    embedded: "Sequence[Schema | Reference]",
    placeholder_keys: Mapping[str, SchemaKey],
) -> Callable[[SchemaKey], tuple[Any, set[Any]]]:
    normalised_embeds: dict[int, tuple[Any, set[Any]]] = {}

    def node_of(key: SchemaKey) -> Any:
        return pair if (pair := (key.resolver, key.identity)) in pairs else key

    def normalised_embed(index: int) -> tuple[Any, set[Any]]:
        if index not in normalised_embeds:
            found: set[Any] = set()

            def replace(ref: str) -> Any:
                if (key := placeholder_keys.get(ref)) is None:
                    return ref
                found.add(target := node_of(key))
                return target

            normalised_embeds[index] = (map_references(embedded[index].to_schema(), replace), found)
        return normalised_embeds[index]

    def normalised(key: SchemaKey) -> tuple[Any, set[Any]]:
        node = nodes[key]
        found: set[Any] = set()

        def replace(ref: str) -> Any:
            if (target_key := node.references.get(ref)) is not None:
                found.add(target := node_of(target_key))
                return target
            if (index := embed_index(ref)) is not None:
                content, targets = normalised_embed(index)
                found.update(targets)
                return content
            return ref

        return map_references(node.schema, replace), found

    return normalised


def merge_identical_modes(
    nodes: Mapping[SchemaKey, SchemaNode],
    embedded: "Sequence[Schema | Reference]",
    placeholder_keys: Mapping[str, SchemaKey],
) -> set[Pair]:
    """Find the identities documented in both modes whose two schemas become one component.

    Schemas are compared with references to other pairs and embedded Litestar schemas normalised, since those
    targets may themselves be merged: a reference to a pair becomes the pair, any other reference its key, and an
    embedded schema its content, in which placeholders become the pair or key of their schema. A pair stays split if
    its schemas differ or it refers to a pair that stays split, found by one walk over the reverse references, so a
    merged schema never refers to a mode-specific one.

    Args:
        nodes: The nodes of every resolver.
        embedded: The embedded Litestar schemas, by index.
        placeholder_keys: The key of the schema of each placeholder.

    Returns:
        The ``(resolver, identity)`` pairs to merge.
    """
    pairs: set[Pair] = {
        (key.resolver, key.identity)
        for key in nodes
        if key.mode == "validation" and SchemaKey(key.resolver, key.identity, "serialization") in nodes
    }
    normalised = _normaliser(nodes, pairs, embedded, placeholder_keys)
    referrers: dict[Pair, list[Pair]] = {}
    split: set[Pair] = set()
    for pair in pairs:
        resolver, identity = pair
        (validation, from_validation), (serialization, from_serialization) = (
            normalised(SchemaKey(resolver, identity, mode)) for mode, _ in MODES
        )
        for target in (from_validation | from_serialization) & pairs:
            referrers.setdefault(target, []).append(pair)
        if validation != serialization:
            split.add(pair)
    stack = list(split)
    while stack:
        for referrer in referrers.get(stack.pop(), ()):
            if referrer not in split:
                split.add(referrer)
                stack.append(referrer)
    return pairs - split


def collapse_merged(resolved: ResolvedSchemas, merged: Collection[Pair]) -> ResolvedSchemas:
    """Make each merged pair one node, keyed and shaped like its validation schema.

    Args:
        resolved: The schemas of one resolver.
        merged: The ``(resolver, identity)`` pairs to merge.

    Returns:
        ``resolved`` without the serialization nodes of merged pairs, with every key of such a pair replaced by its
        validation key.
    """
    if not any((key.resolver, key.identity) in merged for key in resolved.nodes if key.mode == "serialization"):
        return resolved

    def canonical(key: SchemaKey) -> SchemaKey:
        if key.mode == "serialization" and (key.resolver, key.identity) in merged:
            return SchemaKey(key.resolver, key.identity, "validation")
        return key

    nodes: dict[SchemaKey, SchemaNode] = {}
    for key, node in resolved.nodes.items():
        if canonical(key) is not key:
            continue
        references = {ref: canonical(target) for ref, target in node.references.items()}
        changed = any(references[ref] is not target for ref, target in node.references.items())
        nodes[key] = SchemaNode(node.schema, references, node.names) if changed else node
    roots = {request: canonical(key) for request, key in resolved.roots.items()}
    return ResolvedSchemas(roots, nodes, resolved.warnings)
