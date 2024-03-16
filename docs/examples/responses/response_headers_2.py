from random import randint

from pydantic import BaseModel

from litestar import Litestar, Response, get
from litestar.datastructures import ResponseHeader


class Resource(BaseModel):
    id: int
    name: str


@get(
    "/resources",
    response_headers=[
        ResponseHeader(
            name="Random-Header",
            description="a random number in the range 1 - 100",
            documentation_only=True,
        )
    ],
    sync_to_thread=False,
)
def retrieve_resource() -> Response[Resource]:
    return Response(
        Resource(
            id=1,
            name="my resource",
        ),
        headers={"Random-Header": str(randint(1, 100))},
    )


app = Litestar(route_handlers=[retrieve_resource])
