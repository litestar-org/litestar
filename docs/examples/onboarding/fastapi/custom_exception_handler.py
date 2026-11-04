from litestar import Litestar, Request, Response, get


class ItemNotFoundError(Exception):
    pass


def handle_item_not_found(request: Request, exception: ItemNotFoundError) -> Response[dict[str, str]]:
    return Response({"detail": "item not found"}, status_code=404)


@get("/")
async def index() -> None:
    raise ItemNotFoundError


app = Litestar(
    route_handlers=[index],
    exception_handlers={ItemNotFoundError: handle_item_not_found},
)
