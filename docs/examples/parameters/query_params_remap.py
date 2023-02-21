from typing import Dict

from starlite import Starlite, get
from starlite.params import Parameter


@get("/")
def index(snake_case: str = Parameter(query="camelCase")) -> Dict[str, str]:
    return {"param": snake_case}


app = Starlite(route_handlers=[index])

# run: /?camelCase=foo
