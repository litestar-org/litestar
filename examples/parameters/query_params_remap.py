from typing import Dict

from starlite import Parameter, Starlite, get


@get("/")
def index(snake_case: str = Parameter(query="camelCase")) -> Dict[str, str]:
    return {"param": snake_case}


app = Starlite(route_handlers=[index])
