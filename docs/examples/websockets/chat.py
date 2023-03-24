from asyncio import gather
from pathlib import Path
from uuid import uuid4

from starlite import Starlite, WebSocket, websocket
from starlite.datastructures.state import State
from starlite.events import listener
from starlite.exceptions import WebSocketDisconnect
from starlite.static_files import StaticFilesConfig


class MyState(State):
    websockets: dict[str, WebSocket]


@listener("ws_receive")
async def on_ws_receive(sender_id: str, message: str) -> None:
    state: MyState = app.state
    message_container = {"from": sender_id, "message": message}
    await gather(*[socket.send_json(message_container) for socket in state.websockets.values()])


@websocket("/chat")
async def chat(socket: WebSocket, state: MyState) -> None:
    await socket.accept()
    client_id = uuid4().hex
    await socket.send_json({"from": "Server", "message": f"Connected as {client_id}"})
    state.websockets[client_id] = socket
    while True:
        try:
            message = await socket.receive_text()
        except WebSocketDisconnect:
            del state.websockets[client_id]
            break
        else:
            app.emit("ws_receive", client_id, message)


app = Starlite(
    route_handlers=[chat],
    listeners=[on_ws_receive],
    state=State({"websockets": {}}),
    static_files_config=[
        StaticFilesConfig(
            directories=[Path("static")],
            path="/",
            html_mode=True,
        )
    ],
)
