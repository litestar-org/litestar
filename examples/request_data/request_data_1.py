from typing import Dict

from starlite import Starlite, post


@post(path="/")
async def index(data: Dict[str, str]) -> Dict[str, str]:
    return data


app = Starlite(route_handlers=[index])
