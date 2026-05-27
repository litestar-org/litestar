from litestar import Litestar, Request, Response, get
from litestar.exceptions import HTTPException


def handle_http_exception(request: Request, exception: HTTPException) -> Response[dict[str, str]]:
    return Response(
        {"detail": exception.detail},
        status_code=exception.status_code,
    )


@get("/", sync_to_thread=False)
def index() -> None:
    raise HTTPException(status_code=400, detail="this did not work")


app = Litestar(
    route_handlers=[index],
    exception_handlers={HTTPException: handle_http_exception},
)
