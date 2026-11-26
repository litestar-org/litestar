import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
from msgspec import to_builtins

from litestar.dto import DataclassDTO, DTOConfig, DTOData
from litestar.dto._backend import DTOBackend
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar import Request


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
    child: "ChainNode | None" = None


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
    model: type[Any],
    config: DTOConfig,
    *,
    is_data_field: bool,
    accessor: Any = None,
    annotation: Any = None,
) -> "DTOBackend":
    namespace: dict[str, Any] = {"config": config}
    if accessor is not None:
        namespace["attribute_accessor"] = staticmethod(accessor)
    dto_base: Any = DataclassDTO
    dto: Any = type("NestedTransferDTO", (dto_base[model],), namespace)
    return DTOBackend(
        dto_factory=dto,
        field_definition=FieldDefinition.from_annotation(model if annotation is None else annotation),
        handler_id="test",
        is_data_field=is_data_field,
        model_type=model,
        wrapper_attribute_name=None,
    )


def _generated_sources(model: type[Any], max_nested_depth: int) -> list[str]:
    backend = _create_backend(model, DTOConfig(max_nested_depth=max_nested_depth), is_data_field=False)
    return [inspect.getsource(fn) for fn in backend._transfer_function_cache.values()]


@pytest.mark.parametrize("as_mapping", [False, True])
def test_nested_models_below_nested_models_are_encoded(as_mapping: bool) -> None:
    backend = _create_backend(
        DeepRoot, DTOConfig(max_nested_depth=3, exclude={"middle.leaf.y", "id"}), is_data_field=False
    )
    source = _deep_root_with_mapping_levels() if as_mapping else _deep_root()

    expected = _deep_root_builtins()
    del expected["id"]
    del expected["middle"]["leaf"]["y"]
    assert to_builtins(backend.encode_data(source)) == expected


def test_nested_models_below_nested_models_are_decoded(asgi_connection: "Request[Any, Any, Any]") -> None:
    backend = _create_backend(DeepRoot, DTOConfig(max_nested_depth=3), is_data_field=True)

    assert backend.populate_data_from_builtins(_deep_root_builtins(), asgi_connection) == _deep_root()


def test_nested_model_exclude_is_kept_per_path_when_encoding() -> None:
    backend = _create_backend(DeepRoot, DTOConfig(max_nested_depth=3, exclude={"middle.leaf.y"}), is_data_field=False)

    encoded: Any = to_builtins(backend.encode_data(_deep_root()))

    assert encoded["middle"]["leaf"] == {"x": 10}
    assert encoded["maybe_middle"]["leaf"] == {"x": 30, "y": "y"}


def test_nested_model_exclude_is_kept_per_path_when_decoding(asgi_connection: "Request[Any, Any, Any]") -> None:
    backend = _create_backend(DeepRoot, DTOConfig(max_nested_depth=3, exclude={"middle.leaf.y"}), is_data_field=True)
    builtins = _deep_root_builtins()
    builtins["middle"]["leaf"] = {"x": 10, "y": "dropped"}
    builtins["maybe_middle"]["leaf"] = {"x": 30, "y": "kept"}

    data = backend.populate_data_from_builtins(builtins, asgi_connection)

    assert data.middle.leaf == DeepLeaf(x=10, y="y")
    assert data.maybe_middle.leaf == DeepLeaf(x=30, y="kept")


def test_nested_optional_model_in_dto_data_builtins(asgi_connection: "Request[Any, Any, Any]") -> None:
    backend = _create_backend(DeepRoot, DTOConfig(max_nested_depth=3), is_data_field=True, annotation=DTOData[DeepRoot])

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


@pytest.mark.parametrize("as_mapping", [False, True])
def test_custom_attribute_accessor_reads_deeply_nested_models_once(as_mapping: bool) -> None:
    calls: list[tuple[str, str]] = []

    def accessor(obj: object, name: str) -> Any:
        calls.append((type(obj).__name__, name))
        return getattr(obj, name)

    backend = _create_backend(DeepRoot, DTOConfig(max_nested_depth=3), is_data_field=False, accessor=accessor)
    source = _deep_root_with_mapping_levels() if as_mapping else _deep_root()

    assert to_builtins(backend.encode_data(source)) == _deep_root_builtins()
    assert calls.count(("DeepRoot", "middle")) == (0 if as_mapping else 1)
    assert calls.count(("DeepLink", "middle")) == (0 if as_mapping else 1)
    assert calls.count(("DeepMiddle", "leaf")) == 4


def test_generated_source_grows_linearly_with_nested_depth() -> None:
    sources = {depth: _generated_sources(ChainNode, max_nested_depth=depth) for depth in (2, 4, 8)}
    counts = {depth: len(source) for depth, source in sources.items()}
    sizes = {depth: sum(map(len, source)) for depth, source in sources.items()}

    assert counts[8] - counts[4] == 2 * (counts[4] - counts[2])
    assert (sizes[8] - sizes[4]) / (sizes[4] - sizes[2]) <= 2.1
