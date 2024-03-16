from litestar import Litestar, Request, Response, get
from litestar.exceptions import HTTPException, ValidationException


def app_exception_handler(request: Request, exc: HTTPException) -> Response:
    return Response(
        content={
            "error": "server error",
            "path": request.url.path,
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
        status_code=500,
    )


def router_handler_exception_handler(
    request: Request, exc: ValidationException
) -> Response:
    return Response(
        content={"error": "validation error", "path": request.url.path},
        status_code=400,
    )


@get("/")
async def index() -> None:
    raise HTTPException("something's gone wrong")


@get(
    "/greet",
    exception_handlers={ValidationException: router_handler_exception_handler},
)
async def greet(name: str) -> str:
    return f"hello {name}"


app = Litestar(
    route_handlers=[index, greet],
    exception_handlers={HTTPException: app_exception_handler},
)


# run: /
# run: /greet
