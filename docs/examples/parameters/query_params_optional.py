from typing import Dict, Optional

from litestar import Litestar, get


@get("/", sync_to_thread=False)
def index(param: Optional[str] = None) -> Dict[str, Optional[str]]:
    return {"param": param}


app = Litestar(route_handlers=[index])


# run: /
# run: /?param=goodbye
