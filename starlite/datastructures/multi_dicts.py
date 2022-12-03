from abc import ABC
from typing import (
    Any,
    Dict,
    Generator,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from multidict import MultiDict as BaseMultiDict
from multidict import MultiDictProxy, MultiMapping

from starlite.datastructures.upload_file import UploadFile
from starlite.utils import deprecated

T = TypeVar("T")


class MultiMixin(Generic[T], MultiMapping[T], ABC):
    """Mixin providing common methods for multi dicts, used by.

    [ImmutableMultiDict][starlite.datastructures.multi_dicts.ImmutableMultiDict] and
    [MultiDict][starlite.datastructures.multi_dicts.MultiDict]
    """

    def dict(self) -> Dict[str, List[Any]]:
        """Return the multi-dict as a dict of lists.

        Returns:
            A dict of lists
        """
        return {k: self.getall(k) for k in set(self.keys())}

    def multi_items(self) -> Generator[Tuple[str, T], None, None]:
        """Get all keys and values, including duplicates.

        Returns:
            A list of tuples containing key-value pairs
        """
        for key in set(self):
            for value in self.getall(key):
                yield key, value

    @deprecated("1.36.0", alternative="FormMultiDict.getall")
    def getlist(self, key: str) -> List[T]:
        """Get all values.

        Args:
            key: The key

        Returns:
            A list of values
        """
        return super().getall(key, [])


class MultiDict(BaseMultiDict[T], MultiMixin[T], Generic[T]):
    """MultiDict, using [MultiDict][multidict.MultiDictProxy]."""

    def __init__(self, args: Optional[Union["MultiMapping", Mapping[str, T], Iterable[Tuple[str, T]]]] = None) -> None:
        """Initialize `MultiDict` from a.

        [MultiMapping][multidict.MultiMapping], `Mapping` or an iterable of
        tuples.

        Args:
            args: Mapping-like structure to create the `MultiDict` from
        """
        super().__init__(args or {})

    def immutable(self) -> "ImmutableMultiDict[T]":
        """Create an.

        [ImmutableMultiDict][starlite.datastructures.multi_dicts.ImmutableMultiDict] view.

        Returns:
            An immutable multi dict
        """
        return ImmutableMultiDict[T](self)


class ImmutableMultiDict(MultiDictProxy[T], MultiMixin[T], Generic[T]):
    """Immutable MultiDict, using.

    [MultiDictProxy][multidict.MultiDictProxy].
    """

    def __init__(
        self, args: Optional[Union["MultiMapping", Mapping[str, Any], Iterable[Tuple[str, Any]]]] = None
    ) -> None:
        """Initialize `ImmutableMultiDict` from a.

        [MultiMapping][multidict.MultiMapping], `Mapping` or an iterable of
        tuples.

        Args:
            args: Mapping-like structure to create the `ImmutableMultiDict` from
        """
        super().__init__(BaseMultiDict(args or {}))

    def mutable_copy(self) -> MultiDict[T]:
        """Create a mutable copy as a.

        [MultiDict][starlite.datastructures.multi_dicts.MultiDict]

        Returns:
            A mutable multi dict
        """
        return MultiDict(list(self.multi_items()))


class FormMultiDict(ImmutableMultiDict[Any]):
    """MultiDict for form data."""

    async def close(self) -> None:
        """Close all files in the multi-dict.

        Returns:
            None
        """
        for _, value in self.multi_items():
            if isinstance(value, UploadFile):
                await value.close()
