from typing import Dict

from starlite import Starlite, websocket_listener


@websocket_listener("/")
async def handler(data: str) -> Dict[str, str]:
    return {"message": data}


app = Starlite([handler])
