from typing import Dict

from starlite import Starlite, get
from starlite.params import Parameter


@get("/")
def index(param: int = Parameter(gt=5)) -> Dict[str, int]:
    return {"param": param}


app = Starlite(route_handlers=[index])
