from starlite import Starlite, get
from starlite.datastructures import State


class MyState(State):
    count: int = 0

    def increment(self) -> None:
        self.count += 1


@get("/")
def handler(state: MyState) -> dict:
    state.increment()
    return state.dict()


app = Starlite(route_handlers=[handler])
