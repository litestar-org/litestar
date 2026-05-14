from typing import Dict, Optional

from litestar import Litestar, get
from litestar.params import FromQuery


@get("/", sync_to_thread=False)
def index(param: FromQuery[Optional[str]] = None) -> Dict[str, Optional[str]]:
    return {"param": param}


app = Litestar(route_handlers=[index])


# run: /
# run: /?param=goodbye
