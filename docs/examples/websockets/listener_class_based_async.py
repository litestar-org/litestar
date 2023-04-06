from starlite import Starlite, WebSocket
from starlite.handlers import WebsocketListener


class Handler(WebsocketListener):
    path = "/"

    async def on_accept(self, socket: WebSocket) -> None:
        print("Connection accepted")

    async def on_disconnect(self, socket: WebSocket) -> None:
        print("Connection closed")

    async def on_receive(self, data: str) -> str:
        return data


app = Starlite([Handler])
