from litestar import Litestar, get
from litestar.datastructures import State


@get("/")
def handler(state: State) -> dict:
    return state.dict()


app = Litestar(route_handlers=[handler], state=State({"count": 100}))
