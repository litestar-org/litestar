from typing import Annotated, Dict

from litestar import Litestar, get
from litestar.params import Parameter


@get("/")
def index(snake_case: Annotated[str, Parameter(query="camelCase")]) -> Dict[str, str]:
    return {"param": snake_case}


app = Litestar(route_handlers=[index])

# run: /?camelCase=foo
