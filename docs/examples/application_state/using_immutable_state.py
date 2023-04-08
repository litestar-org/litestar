from litestar import Litestar, get
from litestar.datastructures import ImmutableState


@get("/")
def handler(state: ImmutableState) -> dict:
    setattr(state, "count", 1)  # raises AttributeError
    return state.dict()


app = Litestar(route_handlers=[handler])
