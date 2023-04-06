from typing import Dict

from starlite import Starlite, websocket_listener


@websocket_listener("/")
async def handler(data: Dict[str, str]) -> Dict[str, str]:
    return data


app = Starlite([handler])
