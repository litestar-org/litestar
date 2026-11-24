import dataclasses
import functools
from collections.abc import Callable
from typing import Annotated, Any, Final, Generic, Literal, TypeVar

import msgspec
import pytest

from litestar.dto import DataclassDTO, DTOField, Mark, MsgspecDTO

Library = Literal["dc", "ms", "py"]
LIBRARIES: Final[tuple[Library, ...]] = ("dc", "ms", "py")

T = TypeVar("T")

REQUIRED: Final[Any] = object()
PRIVATE: Final = DTOField(mark=Mark.PRIVATE)
READ_ONLY: Final = DTOField(mark=Mark.READ_ONLY)
WRITE_ONLY: Final = DTOField(mark=Mark.WRITE_ONLY)


@dataclasses.dataclass(frozen=True)
class Factory:
    make: Callable[[], Any]


@dataclasses.dataclass(frozen=True)
class F:
    name: str
    annotation: Any
    default: Any = REQUIRED


@dataclasses.dataclass
class Envelope(Generic[T]):
    data: T
    count: int


@dataclasses.dataclass
class Page(Generic[T]):
    items: list[T]
    total: int


@dataclasses.dataclass
class DcShout:
    name: str

    @property
    def loud(self) -> str:
        return self.name.upper()


class MsShout(msgspec.Struct):
    name: str

    @property
    def loud(self) -> str:
        return self.name.upper()


@dataclasses.dataclass
class DcNode:
    name: str
    children: list["DcNode"] = dataclasses.field(default_factory=list)


class MsNode(msgspec.Struct):
    name: str
    children: list["MsNode"] = []


DcShout.__name__ = MsShout.__name__ = "Shout"
DcNode.__name__ = MsNode.__name__ = "Node"


def _pydantic_node() -> Any:
    import pydantic

    fields: dict[str, Any] = {"name": (str, ...), "children": ("list[Node]", [])}
    node = pydantic.create_model("Node", **fields)
    node.model_rebuild()
    return node


def _pydantic_shout() -> Any:
    import pydantic

    class Shout(pydantic.BaseModel):
        name: str

        @pydantic.computed_field
        def loud(self) -> str:
            return self.name.upper()

    return Shout


class Maker:
    def __init__(self, library: Library) -> None:
        self.library: Final = library

    @property
    def dto(self) -> Any:
        if self.library == "dc":
            return DataclassDTO
        if self.library == "ms":
            return MsgspecDTO
        from litestar.plugins.pydantic import PydanticDTO

        return PydanticDTO

    @functools.cached_property
    def shout(self) -> Any:
        if self.library == "dc":
            return DcShout
        if self.library == "ms":
            return MsShout
        return _pydantic_shout()

    @functools.cached_property
    def node(self) -> Any:
        if self.library == "dc":
            return DcNode
        if self.library == "ms":
            return MsNode
        return _pydantic_node()

    def constrained(self, annotation: Any, **constraints: Any) -> Any:
        if self.library == "py":
            import pydantic

            return Annotated[annotation, pydantic.Field(**constraints)]
        return Annotated[annotation, msgspec.Meta(**constraints)]

    def model(self, name: str, *fields: F, frozen: bool = False) -> Any:
        if self.library == "dc":
            return dataclasses.make_dataclass(
                name,
                [(field.name, field.annotation, _dataclass_field(field)) for field in fields],
                frozen=frozen,
                kw_only=True,
            )
        if self.library == "ms":
            return msgspec.defstruct(name, [_struct_field(field) for field in fields], frozen=frozen, kw_only=True)
        import pydantic

        definitions: dict[str, Any] = {field.name: (field.annotation, _pydantic_default(field)) for field in fields}
        return pydantic.create_model(name, __config__=pydantic.ConfigDict(frozen=frozen), **definitions)


def maker(library: Library) -> Maker:
    if library == "py":
        pytest.importorskip("pydantic")
    return Maker(library)


def _dataclass_field(field: F) -> Any:
    if field.default is REQUIRED:
        return dataclasses.field()
    if isinstance(field.default, Factory):
        return dataclasses.field(default_factory=field.default.make)
    return dataclasses.field(default=field.default)


def _struct_field(field: F) -> Any:
    if field.default is REQUIRED:
        return (field.name, field.annotation)
    if isinstance(field.default, Factory):
        return (field.name, field.annotation, msgspec.field(default_factory=field.default.make))
    return (field.name, field.annotation, field.default)


def _pydantic_default(field: F) -> Any:
    import pydantic

    if field.default is REQUIRED:
        return ...
    if isinstance(field.default, Factory):
        return pydantic.Field(default_factory=field.default.make)
    return field.default
