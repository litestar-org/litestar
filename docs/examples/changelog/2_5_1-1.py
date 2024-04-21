import msgspec

from litestar import get
from litestar.testing import create_test_client


class StructA(msgspec.Struct):
    pass


class StructB(msgspec.Struct):
    pass


@get("/")
async def handler() -> StructA | StructB | None:
    return StructA()