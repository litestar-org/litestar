from litestar import Litestar, WebSocket
from litestar.handlers import WebsocketListener


class Handler(WebsocketListener):
    path = "/"

    async def on_accept(self, socket: WebSocket) -> None:
        print("Connection accepted")

    async def on_disconnect(self, socket: WebSocket) -> None:
        print("Connection closed")

    async def on_receive(self, data: str) -> str:
        return data


app = Litestar([Handler])
