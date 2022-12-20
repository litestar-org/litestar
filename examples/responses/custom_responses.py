from starlite import Response, Starlite, get
from starlite.datastructures import MultiDict
from starlite.utils.serialization import DEFAULT_TYPE_ENCODERS


class MultiDictResponse(Response):
    type_encoders = {
        **DEFAULT_TYPE_ENCODERS,
        MultiDict: lambda d: d.dict(),
    }


@get("/")
async def index() -> MultiDict:
    return MultiDict([("foo", "bar"), ("foo", "baz")])


app = Starlite([index], response_class=MultiDictResponse)


# run: /
