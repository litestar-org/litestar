from litestar import Litestar, Request, get
from litestar.params import FromPath
from litestar.response import Redirect


@get("/", name="index")
async def index() -> dict[str, str]:
    return {"page": "index"}


@get("/{item_id:int}", name="item-detail")
async def item_detail(item_id: FromPath[int]) -> dict[str, int]:
    return {"id": item_id}


@get("/redirect")
async def to_index(request: Request) -> Redirect:
    return Redirect(path=request.url_for("index"))


app = Litestar(route_handlers=[index, item_detail, to_index])
