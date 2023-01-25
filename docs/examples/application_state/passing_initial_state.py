from starlite import Starlite, State, get


@get("/")
def handler(state: State) -> dict:
    return state.dict()


app = Starlite(route_handlers=[handler], initial_state={"count": 100})
