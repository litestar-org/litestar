from litestar import Litestar, post
from litestar.params import JSONBody


@post(path="/")
async def index(data: JSONBody[dict[str, str]]) -> dict[str, str]:
    return data


app = Litestar(route_handlers=[index])
