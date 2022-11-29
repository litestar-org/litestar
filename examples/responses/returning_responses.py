from pydantic import BaseModel

from starlite import Response, Starlite, get
from starlite.datastructures import Cookie


class Resource(BaseModel):
    id: int
    name: str


@get("/resources")
def retrieve_resource() -> Response[Resource]:
    return Response(
        Resource(
            id=1,
            name="my resource",
        ),
        headers={"MY-HEADER": "xyz"},
        cookies=[Cookie(key="my-cookie", value="abc")],
    )


app = Starlite(route_handlers=[retrieve_resource])
