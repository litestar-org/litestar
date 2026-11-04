from litestar import Litestar, websocket_listener


@websocket_listener("/ws")
async def chat(data: str) -> str:
    return f"you said: {data}"


app = Litestar(route_handlers=[chat])
