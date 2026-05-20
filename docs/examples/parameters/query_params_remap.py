from typing import Dict

from typing_extensions import Annotated

from litestar import Litestar, get
from litestar.params import QueryParameter


@get("/", sync_to_thread=False)
def index(snake_case: Annotated[str, QueryParameter(name="camelCase")]) -> Dict[str, str]:
    return {"param": snake_case}


app = Litestar(route_handlers=[index])

# run: /?camelCase=foo
