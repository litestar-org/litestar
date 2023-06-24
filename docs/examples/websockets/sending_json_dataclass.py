from dataclasses import dataclass
from datetime import datetime

from litestar import Litestar, websocket_listener


@dataclass
class Message:
    content: str
    timestamp: float


@websocket_listener("/")
async def handler(data: str) -> Message:
    return Message(content=data, timestamp=datetime.now().timestamp())


app = Litestar([handler])
