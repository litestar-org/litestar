from starlite import Starlite, websocket_listener


@websocket_listener("/")
async def handler(data: str) -> bytes:
    return data.encode("utf-8")


app = Starlite([handler])
