from typing import Annotated

from litestar import Litestar, get
from litestar.params import QueryParameter


@get("/", sync_to_thread=False)
def index(param: Annotated[int, QueryParameter(gt=5)]) -> dict[str, int]:
    return {"param": param}


app = Litestar(route_handlers=[index])
