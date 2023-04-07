from litestar import Litestar, WebSocket
from litestar.handlers import WebsocketListener


class Handler(WebsocketListener):
    path = "/"

    def on_accept(self, socket: WebSocket) -> None:
        print("Connection accepted")

    def on_disconnect(self, socket: WebSocket) -> None:
        print("Connection closed")

    def on_receive(self, data: str) -> str:
        return data


app = Litestar([Handler])
