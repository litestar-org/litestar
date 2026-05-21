from typing import Annotated

from litestar import get
from litestar.params import PathParameter, QueryParameter


@get("/{some_path:str}")
async def handler(
    some_path: Annotated[str, PathParameter(description="This is the path parameter")],
    some_query: Annotated[int, QueryParameter(gt=1)],
) -> None:
    return None
