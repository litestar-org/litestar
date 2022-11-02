from typing import Any, Iterable, List, Mapping, Optional, Tuple, Union

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
