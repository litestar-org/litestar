from pydantic import BaseModel

from litestar import Litestar, Response, get
from litestar.datastructures import Cookie


class Resource(BaseModel):
    id: int
    name: str


@get("/resources", sync_to_thread=False)
def retrieve_resource() -> Response[Resource]:
    return Response(
        Resource(
            id=1,
            name="my resource",
        ),
        headers={"MY-HEADER": "xyz"},
        cookies=[Cookie(key="my-cookie", value="abc")],
    )


app = Litestar(route_handlers=[retrieve_resource])
