from typing import Dict

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.params import QueryParameter


@get("/", sync_to_thread=False)
def index(param: Annotated[int, QueryParameter(gt=5)]) -> Dict[str, int]:
    return {"param": param}


app = Litestar(route_handlers=[index])
