from litestar import Litestar, Response, get
from litestar.datastructures import MultiDict


class MultiDictResponse(Response):
    type_encoders = {MultiDict: lambda d: d.dict()}


@get("/")
async def index() -> MultiDict:
    return MultiDict([("foo", "bar"), ("foo", "baz")])


app = Litestar([index], response_class=MultiDictResponse)


# run: /
