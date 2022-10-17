# nopycln: file

from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from typing import Type, Union

    from pydantic_factories.protocols import DataclassProtocol
    from typing_extensions import TypeAlias, TypedDict


__all__ = [
    "DataclassType",
    "DataclassTypeOrInstance",
    "TypedDictType",
]

DataclassType: "TypeAlias" = "Type[DataclassProtocol]"

DataclassTypeOrInstance: "TypeAlias" = "Union[DataclassType, DataclassProtocol]"

# mypy issue: https://github.com/python/mypy/issues/11030
TypedDictType: "TypeAlias" = "Type[TypedDict]"  # type:ignore[valid-type]
