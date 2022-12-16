from typing import Dict

from starlite import Starlite, get


@get("/")
def index(param: str = "hello") -> Dict[str, str]:
    return {"param": param}


app = Starlite(route_handlers=[index])


# run: /
# run: /?param=john
