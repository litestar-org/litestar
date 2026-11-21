from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest

from litestar._openapi.schema_generation.library import MODES, LibraryRequest, LibraryResolver, LibraryRun, SchemaMode
from litestar._openapi.schema_generation.library.converter import EMBED_PREFIX
from litestar._openapi.schema_generation.library.exceptions import SchemaNameConflictError
from litestar._openapi.schema_generation.library.graph import (
    NameCandidates,
    ResolvedSchemas,
    SchemaKey,
    SchemaNode,
    collapse_merged,
    merge_identical_modes,
    reachable,
    schema_node,
)
from litestar._openapi.schema_generation.library.naming import Names, name_components
from litestar.openapi.spec import Reference, Schema


class Stub(LibraryResolver):
    def __init__(self, name: str) -> None:
        self.name = name

    def resolve(self, requests: Sequence[LibraryRequest], run: LibraryRun) -> ResolvedSchemas:
        raise NotImplementedError


A, B = Stub("a"), Stub("b")


@dataclass
class Spec:
    identity: str
    short: str
    qualified: str = ""
    explicit: str | None = None
    modes: tuple[SchemaMode, ...] = ("validation",)
    schema: dict[str, Any] = field(default_factory=dict)
    resolver: Stub = A

    def key(self, mode: SchemaMode = "validation") -> SchemaKey:
        return SchemaKey(self.resolver.name, self.identity, mode)

    def request(self, mode: SchemaMode = "validation", name: str | None = None) -> LibraryRequest:
        return LibraryRequest(self.identity, self.resolver, mode, name)


def ref(identity: str) -> dict[str, Any]:
    return {"type": "object", "properties": {"next": {"$ref": f"#/$defs/{identity}"}}}


def resolve(specs: Sequence[Spec], requests: Sequence[LibraryRequest]) -> dict[str, ResolvedSchemas]:
    resolved: dict[str, ResolvedSchemas] = {}
    for resolver in sorted({spec.resolver.name for spec in specs}):
        own = [spec for spec in specs if spec.resolver.name == resolver]
        targets = {f"#/$defs/{spec.identity}": spec.key() for spec in own}
        nodes = {
            spec.key(mode): schema_node(
                spec.schema, targets, NameCandidates(spec.short, spec.qualified or spec.short, spec.explicit)
            )
            for spec in own
            for mode in spec.modes
        }
        roots = {
            request: SchemaKey(resolver, request.annotation, request.mode)
            for request in requests
            if request.resolver.name == resolver
        }
        resolved[resolver] = ResolvedSchemas(roots, nodes)
    return resolved


def names_of(
    specs: Sequence[Spec],
    requests: Sequence[LibraryRequest],
    existing: Sequence[str] = (),
    merged: set[tuple[str, Any]] | None = None,
) -> Names:
    resolved = {name: collapse_merged(result, merged or set()) for name, result in resolve(specs, requests).items()}
    nodes = {key: node for result in resolved.values() for key, node in result.nodes.items()}
    reached = reachable((key for result in resolved.values() for key in result.roots.values()), nodes)
    return name_components(resolved, requests, reached, existing)


ITEM_1 = Spec("i1", "Item", "m1.Item")
ITEM_2 = Spec("i2", "Item", "m2.Item")
OTHER = Spec("o", "Other", "m.Other")
SPECIAL = Spec("s", "Item", "m.Special", explicit="S")
SAME_1 = Spec("q1", "Item", "m.Item")
SAME_2 = Spec("q2", "Item", "m.Item")
BOTH = Spec("b", "Item", "m.Item", modes=("validation", "serialization"), schema={"type": "object"})
FOO = Spec("foo", "Foo")
NAMED_OTHER = Spec("other", "Other", schema={"type": "string"})
FOO_2 = Spec("foo2", "Foo_2")
SHARED_A = Spec("x", "Shared", schema={"type": "string"})
SHARED_B = Spec("x", "Shared", schema={"type": "integer"}, resolver=B)


@pytest.mark.parametrize(
    ("specs", "requests", "existing", "merged", "expected"),
    [
        pytest.param(
            [ITEM_1, ITEM_2, OTHER],
            [ITEM_1.request(), ITEM_2.request(), OTHER.request()],
            (),
            None,
            ["m1.Item", "m2.Item", "Other"],
            id="1-shared-short-name-takes-qualified",
        ),
        pytest.param(
            [Spec("p", "Pair[int, str]", "m.Pair[int, str]")],
            [Spec("p", "").request()],
            (),
            None,
            ["Pair_int_str_"],
            id="1-runs-of-invalid-characters-collapse",
        ),
        pytest.param(
            [SPECIAL, ITEM_1],
            [SPECIAL.request(), ITEM_1.request()],
            (),
            None,
            ["S", "Item"],
            id="1-explicit-name-uses-qualified-base",
        ),
        pytest.param(
            [SAME_1, SAME_2],
            [SAME_2.request(), SAME_1.request()],
            (),
            None,
            ["m.Item_2", "m.Item"],
            id="1-numeric-suffix-in-nodes-order",
        ),
        pytest.param(
            [BOTH],
            [BOTH.request("validation"), BOTH.request("serialization")],
            (),
            None,
            ["Item-Input", "Item-Output"],
            id="2-unmerged-pair-gets-mode-suffixes",
        ),
        pytest.param(
            [BOTH],
            [BOTH.request("validation"), BOTH.request("serialization")],
            (),
            {("a", "b")},
            ["Item", "Item"],
            id="2-merged-pair-gets-no-suffix",
        ),
        pytest.param(
            [BOTH],
            [BOTH.request("validation", "Custom"), BOTH.request("serialization", "Custom")],
            (),
            None,
            ["Custom-Input", "Custom-Output"],
            id="3-name-requested-in-both-modes-is-suffixed",
        ),
        pytest.param(
            [BOTH],
            [BOTH.request("validation", "Custom")],
            (),
            None,
            ["Custom"],
            id="3-name-requested-in-one-mode-is-not-suffixed",
        ),
        pytest.param(
            [FOO_2, FOO],
            [FOO_2.request(), FOO.request()],
            ["Foo"],
            None,
            ["Foo_2_2", "Foo_2"],
            id="3-automatic-names-follow-intermediate-name-order",
        ),
        pytest.param(
            [FOO, NAMED_OTHER],
            [FOO.request(), NAMED_OTHER.request(name="Foo")],
            (),
            None,
            ["Foo_2", "Foo"],
            id="4-explicit-names-first",
        ),
        pytest.param(
            [Spec("e", "Zed", explicit="Foo", schema={"type": "string"}), FOO],
            [FOO.request(), Spec("e", "").request()],
            (),
            None,
            ["Foo_2", "Foo"],
            id="4-explicit-schema-name-first",
        ),
        pytest.param(
            [Spec("x", "X", schema={"type": "string"}), Spec("y", "Y", schema={"type": "string"})],
            [Spec("x", "").request(name="Same"), Spec("y", "").request(name="Same")],
            (),
            None,
            ["Same", "Same"],
            id="4-equal-schemas-under-one-name-share",
        ),
        pytest.param(
            [SHARED_A, SHARED_B],
            [SHARED_A.request(), SHARED_B.request()],
            (),
            None,
            ["Shared", "Shared_2"],
            id="4-resolver-order-decides-who-keeps-a-name",
        ),
        pytest.param(
            [FOO],
            [FOO.request()],
            ["Foo"],
            None,
            ["Foo_2"],
            id="4-taken-automatic-name-gets-suffix",
        ),
    ],
)
def test_name_components(
    specs: list[Spec],
    requests: list[LibraryRequest],
    existing: Sequence[str],
    merged: set[tuple[str, Any]] | None,
    expected: list[str],
) -> None:
    names = names_of(specs, requests, existing, merged)

    assert [names.component_of_request[request] for request in requests] == expected
    assert set(names.keys) == set(expected) - set(existing)
    assert not set(names.keys) & set(existing)


@pytest.mark.parametrize(
    ("requests", "existing"),
    [
        pytest.param([FOO.request(name="K"), NAMED_OTHER.request(name="K")], (), id="two-schemas"),
        pytest.param([FOO.request(name="Taken")], ("Taken",), id="existing-component"),
    ],
)
def test_taken_explicit_name_raises(requests: list[LibraryRequest], existing: Sequence[str]) -> None:
    with pytest.raises(SchemaNameConflictError, match=r"Cannot use the key '(K|Taken)' for a library-generated"):
        names_of([Spec("foo", "Foo", schema={"type": "integer"}), NAMED_OTHER], requests, existing)


def test_only_reached_schemas_and_request_components_are_named() -> None:
    inner = Spec("inner", "Inner", schema={"type": "string"})
    outer = Spec("outer", "Outer", schema=ref("inner"))
    unused = Spec("unused", "Unused")

    names = names_of([outer, inner, unused], [outer.request(name="Custom")])

    assert names.component_of_request == {outer.request(name="Custom"): "Custom"}
    assert dict(names.component_of) == {inner.key(): "Inner"}
    assert dict(names.keys) == {"Custom": outer.key(), "Inner": inner.key()}
    assert dict(names.bases) == {"Custom": "Custom", "Inner": "Inner"}


def test_folded_names_point_at_the_existing_component() -> None:
    names = names_of([FOO], [FOO.request()], existing=["Foo"])

    folded = names.folded({"Foo_2": "Foo"})

    assert folded.component_of_request == {FOO.request(): "Foo"}
    assert folded.component_of == {FOO.key(): "Foo"}
    assert not folded.keys
    assert not folded.bases
    assert not folded.models


def test_models_drop_the_mode_suffix_of_split_schemas_only() -> None:
    suffixed = Spec("evil", "Evil-Input")

    names = names_of([BOTH, suffixed], [BOTH.request(), BOTH.request("serialization"), suffixed.request()])

    assert dict(names.models) == {"Item-Input": "Item", "Item-Output": "Item", "Evil-Input": "Evil-Input"}


def test_a_merged_schema_named_like_a_mode_suffix_keeps_its_explicit_name() -> None:
    suffixed = Spec("evil", "Evil-Input", modes=("validation", "serialization"), schema={"type": "object"})
    requests = [suffixed.request(name="K"), suffixed.request("serialization", name="K")]

    names = names_of([suffixed], requests, merged={("a", "evil")})

    assert set(names.component_of_request.values()) == {"K"}


def test_reachable_includes_a_root_only_if_referenced() -> None:
    a, b = SchemaKey("a", "a", "validation"), SchemaKey("a", "b", "validation")
    targets = {"#/$defs/a": a, "#/$defs/b": b}
    names = NameCandidates("N", "N")
    nodes = {a: schema_node(ref("b"), targets, names), b: schema_node(ref("b"), targets, names)}

    assert list(reachable([a], nodes)) == [b]
    assert list(reachable([a, b], nodes)) == [b]


def pair_nodes(schemas: Mapping[str, tuple[dict[str, Any], dict[str, Any]]]) -> dict[SchemaKey, SchemaNode]:
    targets = {
        f"#/$defs/{identity}{suffix}": SchemaKey("a", identity, mode) for identity in schemas for mode, suffix in MODES
    }
    names = NameCandidates("N", "N")
    return {
        SchemaKey("a", identity, mode): schema_node(schema, targets, names)
        for identity, both in schemas.items()
        for (mode, _), schema in zip(MODES, both)
    }


def chain(target: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return ref(f"{target}-Input"), ref(f"{target}-Output")


def embedding(index: int) -> dict[str, Any]:
    return {"type": "object", "properties": {"x": {"$ref": f"{EMBED_PREFIX}{index}"}}}


EMBEDDED = [Schema(all_of=[Reference("tok-in")]), Schema(all_of=[Reference("tok-out")])]
PLACEHOLDERS = {"tok-in": SchemaKey("a", "b", "validation"), "tok-out": SchemaKey("a", "b", "serialization")}


@pytest.mark.parametrize(
    ("schemas", "merged"),
    [
        pytest.param({"a": chain("b"), "b": chain("a")}, {"a", "b"}, id="mutually-recursive-pairs-merge"),
        pytest.param(
            {"a": chain("b"), "b": chain("c"), "c": ({"type": "integer"}, {"type": "string"}), "d": chain("b")},
            set(),
            id="chain-to-a-split-pair-stays-split",
        ),
        pytest.param(
            {"a": chain("b"), "b": ({"type": "integer"}, {"type": "integer"}), "c": chain("c")},
            {"a", "b", "c"},
            id="identical-pairs-merge",
        ),
        pytest.param(
            {"a": (embedding(0), embedding(1)), "b": ({"type": "integer"}, {"type": "integer"})},
            {"a", "b"},
            id="identical-through-an-embedded-schema",
        ),
        pytest.param(
            {"a": (embedding(0), embedding(1)), "b": ({"type": "integer"}, {"type": "string"})},
            set(),
            id="split-propagates-through-an-embedded-schema",
        ),
    ],
)
def test_split_propagates_to_referrers(
    schemas: Mapping[str, tuple[dict[str, Any], dict[str, Any]]], merged: set[str]
) -> None:
    assert merge_identical_modes(pair_nodes(schemas), EMBEDDED, PLACEHOLDERS) == {("a", name) for name in merged}


def test_identical_modes_merge_into_the_validation_node() -> None:
    nodes = pair_nodes({"a": chain("b"), "b": ({"type": "integer"}, {"type": "integer"})})
    single = SchemaKey("a", "s", "serialization")
    nodes[single] = schema_node(
        ref("b-Output"), {"#/$defs/b-Output": SchemaKey("a", "b", "serialization")}, NameCandidates("S", "S")
    )
    request = LibraryRequest("a", A, "serialization")
    resolved = ResolvedSchemas({request: SchemaKey("a", "a", "serialization")}, nodes)

    collapsed = collapse_merged(resolved, merge_identical_modes(nodes, [], {}))

    b = SchemaKey("a", "b", "validation")
    assert list(collapsed.nodes) == [SchemaKey("a", "a", "validation"), b, single]
    assert collapsed.roots == {request: SchemaKey("a", "a", "validation")}
    assert dict(collapsed.nodes[SchemaKey("a", "a", "validation")].references) == {"#/$defs/b-Input": b}
    assert dict(collapsed.nodes[single].references) == {"#/$defs/b-Output": b}
