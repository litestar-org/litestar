from litestar import Litestar, get
from litestar.exceptions import HTTPException


@get("/")
async def index() -> None:
    response_fields = {"array": "value"}
    raise HTTPException(
        status_code=400,
        detail=f"can't get that field: {response_fields.get('missing')}",
    )


app = Litestar(route_handlers=[index])
