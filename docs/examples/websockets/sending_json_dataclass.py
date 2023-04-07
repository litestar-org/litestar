from dataclasses import dataclass
from datetime import datetime

from litestar import Litestar, websocket_listener


@dataclass
class Message:
    message: str
    timestamp: float


@websocket_listener("/")
async def handler(data: str) -> Message:
    return Message(message=data, timestamp=datetime.now().timestamp())


app = Litestar([handler])
