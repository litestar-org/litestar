from starlite import Response, Starlite, get
from starlite.datastructures import MultiDict


class MultiDictResponse(Response):
    type_encoders = {MultiDict: lambda d: d.dict()}


@get("/")
async def index() -> MultiDict:
    return MultiDict([("foo", "bar"), ("foo", "baz")])


app = Starlite([index], response_class=MultiDictResponse)


# run: /
