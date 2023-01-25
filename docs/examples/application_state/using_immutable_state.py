from starlite import ImmutableState, Starlite, get


@get("/")
def handler(state: ImmutableState) -> dict:
    setattr(state, "count", 1)  # raises AttributeError
    return state.dict()


app = Starlite(route_handlers=[handler])
