from litestar import Litestar, get
from litestar.exceptions import NotFoundException
from litestar.params import FromPath


@get("/items/{item_id:int}")
async def get_item(item_id: FromPath[int]) -> dict[str, int]:
    if item_id != 1:
        raise NotFoundException(detail=f"item {item_id} does not exist")
    return {"id": item_id}


app = Litestar(route_handlers=[get_item])
