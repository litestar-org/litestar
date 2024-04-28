from litestar import get


async def hello_world() -> str:
    return "Hello, world!"


hello_world = get("/")(hello_world)
