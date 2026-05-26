from litestar import Litestar, get
from litestar.exceptions import HTTPException


@get("/", sync_to_thread=False)
def index() -> None:
    raise HTTPException(status_code=400, detail="this did not work")


app = Litestar(route_handlers=[index])
