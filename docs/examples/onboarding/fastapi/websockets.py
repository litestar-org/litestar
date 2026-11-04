from litestar import Litestar, websocket_listener


@websocket_listener("/ws")
async def echo(data: dict[str, str]) -> dict[str, str]:
    return {"echo": data["message"]}


app = Litestar(route_handlers=[echo])
