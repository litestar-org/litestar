from litestar import get, Litestar


@get("/{name:str}")
async def handler(name: str) -> str:
    return f"Hello {name}"


app = Litestar(route_handlers=[handler])

# run: /john
