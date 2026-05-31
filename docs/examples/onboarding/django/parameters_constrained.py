from typing import Annotated

from litestar import Litestar, get
from litestar.params import PathParameter, QueryParameter


@get("/items/{item_id:int}")
async def get_item(
    item_id: Annotated[int, PathParameter(gt=0)],
    limit: Annotated[int, QueryParameter(gt=0, le=100)],
) -> dict[str, int]:
    return {"id": item_id, "limit": limit}


app = Litestar(route_handlers=[get_item])
