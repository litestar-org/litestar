from litestar import Litestar, websocket_listener


@websocket_listener("/")
async def handler(data: str) -> bytes:
    return data.encode("utf-8")


app = Litestar([handler])
