from typing import Dict

from litestar import Litestar, get
from litestar.params import FromQuery


@get("/", sync_to_thread=False)
def index(param: FromQuery[str]) -> Dict[str, str]:
    return {"param": param}


app = Litestar(route_handlers=[index])

# run: /?param=foo
# run: /?param=bar
