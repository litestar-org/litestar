from collections import defaultdict
from typing import Dict

from starlite import Request, Starlite, get

COUNTER: Dict[str, int] = defaultdict(int)


async def after_response(request: Request) -> None:
    COUNTER[request.url.path] += 1


@get("/hello")
async def hello() -> Dict[str, int]:
    return COUNTER


app = Starlite(route_handlers=[hello], after_response=after_response)


# run: /hello
# run: /hello
