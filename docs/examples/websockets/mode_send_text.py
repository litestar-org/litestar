from litestar import Litestar, websocket_listener


@websocket_listener("/", send_mode="text")
async def handler(data: str) -> str:
    return data


app = Litestar([handler])
