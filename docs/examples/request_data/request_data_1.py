from typing import Dict

from litestar import Litestar, post


@post(path="/")
async def index(data: Dict[str, str]) -> Dict[str, str]:
    return data


app = Litestar(route_handlers=[index])
