from random import randint

from pydantic import BaseModel

from starlite import Response, Router, Starlite, get
from starlite.datastructures import Cookie


class Resource(BaseModel):
    id: int
    name: str


@get(
    "/resources",
    response_cookies=[
        Cookie(
            key="Random-Cookie",
            description="a random number in the range 100 - 1000",
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
        cookies=[Cookie(key="Random-Cookie", value=str(randint(100, 1000)))],
    )


def after_request_handler(response: Response) -> Response:
    response.set_cookie(
        **Cookie(key="Random-Cookie", value=str(randint(1, 100))).dict(
            exclude_none=True, exclude={"documentation_only", "description"}
        )
    )
    return response


router = Router(
    path="/router-path",
    route_handlers=[retrieve_resource],
    after_request=after_request_handler,
    response_cookies=[
        Cookie(
            key="Random-Cookie",
            description="a random number in the range 1 - 100",
            documentation_only=True,
        )
    ],
)

app = Starlite(route_handlers=[router])
