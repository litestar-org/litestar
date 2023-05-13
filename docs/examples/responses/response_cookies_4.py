from random import randint

from pydantic import BaseModel

from litestar import Litestar, Response, Router, get
from litestar.datastructures import Cookie


class Resource(BaseModel):
    id: int
    name: str


@get("/resources", sync_to_thread=False)
def retrieve_resource() -> Resource:
    return Resource(
        id=1,
        name="my resource",
    )


def after_request_handler(response: Response) -> Response:
    response.set_cookie(key="Random-Cookie", value=str(randint(1, 100)))
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

app = Litestar(route_handlers=[router])
