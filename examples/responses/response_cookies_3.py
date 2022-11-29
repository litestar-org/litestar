from random import randint

from pydantic import BaseModel

from starlite import Response, Starlite, get
from starlite.datastructures import Cookie


class Resource(BaseModel):
    id: int
    name: str


@get(
    "/resources",
    response_cookies=[
        Cookie(
            key="Random-Cookie",
            description="a random number in the range 1 - 100",
            documentation_only=True,
        )
    ],
)
def retrieve_resource() -> Response[Resource]:
    return Response(
        Resource(
            id=1,
            name="my resource",
        ),
        cookies=[Cookie(key="Random-Cookie", value=str(randint(1, 100)))],
    )


app = Starlite(route_handlers=[retrieve_resource])
