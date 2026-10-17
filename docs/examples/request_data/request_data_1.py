from typing import Dict

from litestar import Litestar, post
from litestar.params import JSONBody


@post(path="/")
async def index(data: JSONBody[Dict[str, str]]) -> Dict[str, str]:
    return data


app = Litestar(route_handlers=[index])
