from starlite import Starlite, get
from starlite.datastructures import ImmutableState


@get("/")
def handler(state: ImmutableState) -> dict:
    setattr(state, "count", 1)  # raises AttributeError
    return state.dict()


app = Starlite(route_handlers=[handler])
