from litestar import Litestar, get


@get("/", sync_to_thread=False)
def index(param: str | None = None) -> dict[str, str | None]:
    return {"param": param}


app = Litestar(route_handlers=[index])


# run: /
# run: /?param=goodbye
