from typing import Dict

from litestar import Litestar, get
from litestar.params import Parameter


@get("/")
def index(param: int = Parameter(gt=5)) -> Dict[str, int]:
    return {"param": param}


app = Litestar(route_handlers=[index])
