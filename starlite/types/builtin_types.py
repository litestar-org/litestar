from typing import TYPE_CHECKING, Type, Union

from typing_extensions import TypeAlias  # noqa: TC002

if TYPE_CHECKING:
    from typing_extensions import _TypedDictMeta  # type: ignore

    from starlite.types.protocols import DataclassProtocol

DataclassClass: TypeAlias = "Type[DataclassProtocol]"
DataclassClassOrInstance: TypeAlias = "Union[DataclassClass, DataclassProtocol]"
TypedDictClass: TypeAlias = "Type[_TypedDictMeta]"
