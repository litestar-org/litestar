from starlite import Starlite, websocket_listener


@websocket_listener("/", receive_mode="binary")
async def handler(data: str) -> str:
    return data


app = Starlite([handler])
