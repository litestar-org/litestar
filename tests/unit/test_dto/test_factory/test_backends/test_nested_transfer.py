from __future__ import annotations

import linecache
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
from msgspec import to_builtins

from litestar.dto import DataclassDTO, DTOConfig, DTOData
from litestar.dto._codegen_backend import DTOCodegenBackend
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar import Request
    from litestar.dto._backend import DTOBackend


@dataclass
class DeepLeaf:
    x: int
    y: str = "y"


@dataclass
class DeepMiddle:
    a: int
    leaf: DeepLeaf
    maybe_leaf: DeepLeaf | None = None
    leaves: list[DeepLeaf] = field(default_factory=list)


@dataclass
class DeepLink:
    middle: DeepMiddle


@dataclass
class DeepRoot:
    id: int
    middle: DeepMiddle
    link: DeepLink
    maybe_middle: DeepMiddle | None = None
    middles: list[DeepMiddle] = field(default_factory=list)


@dataclass
class ChainNode:
    id: int
    name: str
    child: ChainNode | None = None


@dataclass
class TreeNode:
    name: str
    children: list[TreeNode] = field(default_factory=list)
    parent: TreeNode | None = None


def _deep_middle(a: int) -> DeepMiddle:
    return DeepMiddle(a=a, leaf=DeepLeaf(x=a), maybe_leaf=DeepLeaf(x=a + 1), leaves=[DeepLeaf(x=a + 2)])


def _deep_root() -> DeepRoot:
    return DeepRoot(
        id=1,
        middle=_deep_middle(10),
        link=DeepLink(middle=_deep_middle(20)),
        maybe_middle=_deep_middle(30),
        middles=[_deep_middle(40)],
    )


def _middle_builtins(a: int) -> dict[str, Any]:
    return {
        "a": a,
        "leaf": {"x": a, "y": "y"},
        "maybe_leaf": {"x": a + 1, "y": "y"},
        "leaves": [{"x": a + 2, "y": "y"}],
    }


def _deep_root_builtins() -> dict[str, Any]:
    return {
        "id": 1,
        "middle": _middle_builtins(10),
        "link": {"middle": _middle_builtins(20)},
        "maybe_middle": _middle_builtins(30),
        "middles": [_middle_builtins(40)],
    }


def _deep_root_with_mapping_levels() -> dict[str, Any]:
    root = _deep_root()
    return {
        "id": root.id,
        "middle": root.middle,
        "link": {"middle": root.link.middle},
        "maybe_middle": root.maybe_middle,
        "middles": root.middles,
    }


def _create_backend(
    backend_cls: type[DTOBackend],
    model: type[Any],
    config: DTOConfig,
    *,
    is_data_field: bool,
    accessor: Any = None,
    annotation: Any = None,
) -> DTOBackend:
    namespace: dict[str, Any] = {"config": config}
    if accessor is not None:
        namespace["attribute_accessor"] = staticmethod(accessor)
    dto: Any = type("NestedTransferDTO", (DataclassDTO[model],), namespace)  # type: ignore[valid-type]
    return backend_cls(
        dto_factory=dto,
        field_definition=FieldDefinition.from_annotation(model if annotation is None else annotation),
        handler_id="test",
        is_data_field=is_data_field,
        model_type=model,
        wrapper_attribute_name=None,
    )


def _generated_sources(model: type[Any], max_nested_depth: int) -> list[str]:
    before = set(linecache.cache)
    _create_backend(DTOCodegenBackend, model, DTOConfig(max_nested_depth=max_nested_depth), is_data_field=False)
    return [
        "".join(linecache.getlines(key))
        for key in set(linecache.cache) - before
        if key.startswith("dto_transfer_function_")
    ]


@pytest.mark.parametrize("as_mapping", [False, True])
def test_nested_models_below_nested_models_are_encoded(backend_cls: type[DTOBackend], as_mapping: bool) -> None:
    backend = _create_backend(
        backend_cls, DeepRoot, DTOConfig(max_nested_depth=3, exclude={"middle.leaf.y", "id"}), is_data_field=False
    )
    source = _deep_root_with_mapping_levels() if as_mapping else _deep_root()

    expected = _deep_root_builtins()
    del expected["id"]
    del expected["middle"]["leaf"]["y"]
    assert to_builtins(backend.encode_data(source)) == expected


def test_nested_models_below_nested_models_are_decoded(
    backend_cls: type[DTOBackend], asgi_connection: Request[Any, Any, Any]
) -> None:
    backend = _create_backend(backend_cls, DeepRoot, DTOConfig(max_nested_depth=3), is_data_field=True)

    assert backend.populate_data_from_builtins(_deep_root_builtins(), asgi_connection) == _deep_root()


def test_nested_depth_cut_is_kept_per_path(backend_cls: type[DTOBackend]) -> None:
    backend = _create_backend(backend_cls, DeepRoot, DTOConfig(max_nested_depth=2), is_data_field=False)

    expected = _deep_root_builtins()
    expected["link"] = {"middle": {"a": 20}}
    assert to_builtins(backend.encode_data(_deep_root())) == expected


def test_collection_item_exclude_is_kept_per_path_when_encoding(backend_cls: type[DTOBackend]) -> None:
    backend = _create_backend(
        backend_cls, DeepRoot, DTOConfig(max_nested_depth=3, exclude={"middles.0.leaves.0.y"}), is_data_field=False
    )

    encoded: Any = to_builtins(backend.encode_data(_deep_root()))

    assert encoded["middle"]["leaves"] == [{"x": 12, "y": "y"}]
    assert encoded["middles"][0]["leaves"] == [{"x": 42}]


def test_collection_item_exclude_is_kept_per_path_when_decoding(
    backend_cls: type[DTOBackend], asgi_connection: Request[Any, Any, Any]
) -> None:
    backend = _create_backend(
        backend_cls, DeepRoot, DTOConfig(max_nested_depth=3, exclude={"middles.0.leaves.0.y"}), is_data_field=True
    )
    builtins = _deep_root_builtins()
    builtins["middle"]["leaves"] = [{"x": 12, "y": "kept"}]
    builtins["middles"][0]["leaves"] = [{"x": 42, "y": "dropped"}]

    data = backend.populate_data_from_builtins(builtins, asgi_connection)

    assert data.middle.leaves == [DeepLeaf(x=12, y="kept")]
    assert data.middles[0].leaves == [DeepLeaf(x=42, y="y")]


def test_nested_model_exclude_is_kept_per_path_when_encoding(backend_cls: type[DTOBackend]) -> None:
    backend = _create_backend(
        backend_cls, DeepRoot, DTOConfig(max_nested_depth=3, exclude={"middle.leaf.y"}), is_data_field=False
    )

    encoded: Any = to_builtins(backend.encode_data(_deep_root()))

    assert encoded["middle"]["leaf"] == {"x": 10}
    assert encoded["maybe_middle"]["leaf"] == {"x": 30, "y": "y"}


def test_nested_model_exclude_is_kept_per_path_when_decoding(
    backend_cls: type[DTOBackend], asgi_connection: Request[Any, Any, Any]
) -> None:
    backend = _create_backend(
        backend_cls, DeepRoot, DTOConfig(max_nested_depth=3, exclude={"middle.leaf.y"}), is_data_field=True
    )
    builtins = _deep_root_builtins()
    builtins["middle"]["leaf"] = {"x": 10, "y": "dropped"}
    builtins["maybe_middle"]["leaf"] = {"x": 30, "y": "kept"}

    data = backend.populate_data_from_builtins(builtins, asgi_connection)

    assert data.middle.leaf == DeepLeaf(x=10, y="y")
    assert data.maybe_middle.leaf == DeepLeaf(x=30, y="kept")


@pytest.mark.parametrize("max_nested_depth", [1, 3, 5])
def test_self_referential_model_is_cut_at_max_nested_depth(
    backend_cls: type[DTOBackend], max_nested_depth: int
) -> None:
    backend = _create_backend(backend_cls, ChainNode, DTOConfig(max_nested_depth=max_nested_depth), is_data_field=False)
    node = ChainNode(id=0, name="node-0")
    for level in range(1, 8):
        node = ChainNode(id=level, name=f"node-{level}", child=node)

    encoded: Any = to_builtins(backend.encode_data(node))

    levels = []
    while encoded is not None:
        levels.append(encoded["id"])
        encoded = encoded.get("child")
    assert levels == list(range(7, 6 - max_nested_depth, -1))


def test_codegen_nested_optional_model_in_dto_data_builtins(asgi_connection: Request[Any, Any, Any]) -> None:
    backend = _create_backend(
        DTOCodegenBackend, DeepRoot, DTOConfig(max_nested_depth=3), is_data_field=True, annotation=DTOData[DeepRoot]
    )

    builtins = backend.populate_data_from_builtins(_deep_root_builtins(), asgi_connection).as_builtins()

    middle_overrides = {"maybe_leaf": DeepLeaf(x=11), "leaves": [DeepLeaf(x=12)]}
    assert builtins["middle"] == _middle_builtins(10) | middle_overrides
    assert builtins["maybe_middle"] == DeepMiddle(
        a=30,
        leaf={"x": 30, "y": "y"},  # type: ignore[arg-type]
        maybe_leaf=DeepLeaf(x=31),
        leaves=[DeepLeaf(x=32)],
    )
    assert builtins["middles"] == [_deep_middle(40)]


def test_custom_attribute_accessor_reads_nested_model_once(backend_cls: type[DTOBackend]) -> None:
    calls: list[tuple[str, str]] = []

    def accessor(obj: object, name: str) -> Any:
        calls.append((type(obj).__name__, name))
        return getattr(obj, name)

    backend = _create_backend(
        backend_cls, DeepRoot, DTOConfig(max_nested_depth=2), is_data_field=False, accessor=accessor
    )

    backend.encode_data(_deep_root())

    assert calls.count(("DeepRoot", "middle")) == 1
    assert calls.count(("DeepMiddle", "leaf")) == 3


@pytest.mark.parametrize("as_mapping", [False, True])
def test_custom_attribute_accessor_reads_deeply_nested_models_once(
    backend_cls: type[DTOBackend], as_mapping: bool
) -> None:
    calls: list[tuple[str, str]] = []

    def accessor(obj: object, name: str) -> Any:
        calls.append((type(obj).__name__, name))
        return getattr(obj, name)

    backend = _create_backend(
        backend_cls, DeepRoot, DTOConfig(max_nested_depth=3), is_data_field=False, accessor=accessor
    )
    source = _deep_root_with_mapping_levels() if as_mapping else _deep_root()

    assert to_builtins(backend.encode_data(source)) == _deep_root_builtins()
    assert calls.count(("DeepRoot", "middle")) == (0 if as_mapping else 1)
    assert calls.count(("DeepLink", "middle")) == (0 if as_mapping else 1)
    assert calls.count(("DeepMiddle", "leaf")) == 4


def test_codegen_generated_source_grows_linearly_with_nested_depth() -> None:
    shallow = _generated_sources(ChainNode, max_nested_depth=4)
    deep = _generated_sources(ChainNode, max_nested_depth=8)

    assert len(deep) - len(shallow) <= 8
    assert sum(map(len, deep)) < 2 * sum(map(len, shallow))


def test_codegen_generates_one_function_per_nested_collection_item_type() -> None:
    shallow = _generated_sources(TreeNode, max_nested_depth=3)
    deep = _generated_sources(TreeNode, max_nested_depth=4)

    assert len(deep) < 3 * len(shallow)
    assert len(deep) <= 35
    assert sum(map(len, deep)) < 3 * sum(map(len, shallow))
