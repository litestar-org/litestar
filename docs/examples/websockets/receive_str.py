from litestar import Litestar, websocket_listener


@websocket_listener("/")
async def handler(data: str) -> str:
    return data


app = Litestar([handler])
