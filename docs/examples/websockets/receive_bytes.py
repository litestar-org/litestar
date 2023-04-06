from starlite import Starlite, websocket_listener


@websocket_listener("/")
async def handler(data: bytes) -> str:
    return data.decode("utf-8")


app = Starlite([handler])
