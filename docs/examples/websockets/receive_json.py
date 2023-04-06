from typing import Dict

from litestar import Litestar, websocket_listener


@websocket_listener("/")
async def handler(data: Dict[str, str]) -> Dict[str, str]:
    return data


app = Litestar([handler])
