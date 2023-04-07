from litestar import Litestar, WebSocket, websocket_listener


@websocket_listener("/")
async def handler(data: str, socket: WebSocket) -> str:
    if data == "goodbye":
        await socket.close()

    return data


app = Litestar([handler])
