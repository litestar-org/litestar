from typing import Dict, Optional

from starlite import Starlite, get


@get("/")
def index(param: Optional[str] = None) -> Dict[str, Optional[str]]:
    return {"param": param}


app = Starlite(route_handlers=[index])


# run: /
# run: /?param=goodbye
