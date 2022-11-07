from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union
from urllib.parse import parse_qsl

from multidict import MultiDict, MultiDictProxy

from starlite.datastructures.upload_file import UploadFile
from starlite.utils import deprecated


class FormMultiDict(MultiDictProxy[Any]):
    def __init__(
        self, args: Optional[Union["FormMultiDict", Mapping[str, Any], Iterable[Tuple[str, Any]]]] = None
    ) -> None:
        super().__init__(MultiDict(args or {}))

    def multi_items(self) -> List[Tuple[str, Any]]:
        """Get all keys and values, including duplicates.

        Returns:
            A list of tuples containing key-value pairs
        """
        return [(key, value) for key in set(self) for value in self.getall(key)]

    @deprecated("1.36.0", alternative="FormMultiDict.getall")
    def getlist(self, key: str) -> List[str]:
        """Get all values.

        Args:
            key: The key

        Returns:
            A list of values
        """
        return super().getall(key, [])

    async def close(self) -> None:
        """Closes all files in the multi-dict.

        Returns:
            None
        """
        for _, value in self.multi_items():
            if isinstance(value, UploadFile):
                await value.close()


class QueryMultiDict(MultiDict[Union[str, bool]]):
    def __init__(
        self, args: Optional[Union["QueryMultiDict", Mapping[str, Any], Iterable[Tuple[str, Any]]]] = None
    ) -> None:
        super().__init__(MultiDict(args or {}))

    @classmethod
    def from_query_string(cls, query_string: str) -> "QueryMultiDict":
        """Creates a QueryMultiDict from a query string.

        Args:
            query_string: A query string.

        Returns:
            A QueryMultiDict instance
        """
        _bools = {"true": True, "false": False, "True": True, "False": False}
        return cls(
            (k, v) if v not in _bools else (k, _bools[v]) for k, v in parse_qsl(query_string, keep_blank_values=True)
        )

    def dict(self) -> Dict[str, List[Any]]:
        """

        Returns:
            A dict of lists
        """
        return {k: self.getall(k) for k in set(self.keys())}
