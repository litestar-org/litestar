import msgspec

from litestar import get


class StructA(msgspec.Struct):
    pass


class StructB(msgspec.Struct):
    pass


@get("/")
async def handler() -> StructA | StructB | None:
    return StructA()
