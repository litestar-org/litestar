from typing import Any

from starlette.datastructures import ImmutableMultiDict

from starlite.datastructures.upload_file import UploadFile


class FormMultiDict(ImmutableMultiDict[str, Any]):
    async def close(self) -> None:
        """Closes all files in the multi-dict.

        Returns:
            None
        """
        for _, value in self.multi_items():
            if isinstance(value, UploadFile):
                await value.close()
