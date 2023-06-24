from typing import Any, Dict

from litestar import Litestar, get
from litestar.datastructures import State


@get("/", sync_to_thread=False)
def handler(state: State) -> Dict[str, Any]:
    return state.dict()


app = Litestar(route_handlers=[handler], state=State({"count": 100}))
