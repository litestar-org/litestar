from litestar import Litestar, WebSocket, websocket
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend


@websocket("/ws")
async def handler(socket: WebSocket, channels: ChannelsPlugin) -> None:
    await socket.accept()

    async with channels.subscribe(["some_channel"]) as subscriber:
        async with subscriber.run_in_background(socket.send_text):
            while True:
                await socket.receive_text()
                # do something with the message here


app = Litestar(
    [handler],
    plugins=[ChannelsPlugin(backend=MemoryChannelsBackend())],
)
