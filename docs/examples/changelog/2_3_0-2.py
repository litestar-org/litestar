from msgspec import Struct
from litestar import Litestar, get, Response
from typing import TypeVar, Generic, Optional

T = TypeVar("T")


class ResponseStruct(Struct, Generic[T]):
    code: int
    data: Optional[T]


@get("/")
def test_handler() -> Response[ResponseStruct[str]]:
    return Response(
        ResponseStruct(code=200, data="Hello World"),
    )