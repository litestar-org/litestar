from typing import Dict

from litestar import Litestar, get


@get("/", sync_to_thread=False)
def index(param: str) -> Dict[str, str]:
    return {"param": param}


app = Litestar(route_handlers=[index])

# run: /?param=foo
# run: /?param=bar
