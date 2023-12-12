from litestar import Litestar, WebSocket, websocket
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend


@websocket("/ws")
async def handler(socket: WebSocket, channels: ChannelsPlugin) -> None:
    await socket.accept()

    async with await channels.subscribe(["some_channel"]) as subscriber, subscriber.run_in_background(socket.send_text):
        while True:
            response = await socket.receive_text()
            await subscriber.send(response)


app = Litestar(
    [handler],
    plugins=[ChannelsPlugin(backend=MemoryChannelsBackend(), channels=["some_channel"])],
)
