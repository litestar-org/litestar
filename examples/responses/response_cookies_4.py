from random import randint

from pydantic import BaseModel
from starlite import Starlite, Response, Router, get
from starlite.datastructures import Cookie


class Resource(BaseModel):
    id: int
    name: str


@get("/resources")
def retrieve_resource() -> Resource:
    return Resource(
        id=1,
        name="my resource",
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
