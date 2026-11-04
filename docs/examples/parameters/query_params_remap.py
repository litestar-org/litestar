from typing import Annotated

from litestar import Litestar, get
from litestar.params import QueryParameter


@get("/", sync_to_thread=False)
def index(snake_case: Annotated[str, QueryParameter(name="camelCase")]) -> dict[str, str]:
    return {"param": snake_case}


app = Litestar(route_handlers=[index])

# run: /?camelCase=foo
