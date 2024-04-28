from litestar import get


@get("/{name:str}")
async def greeter(name: str) -> str:
    return "Hello, " + name
