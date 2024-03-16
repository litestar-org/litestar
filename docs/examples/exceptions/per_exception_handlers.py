from litestar import Litestar, MediaType, Request, Response, get
from litestar.exceptions import HTTPException, ValidationException
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR


def validation_exception_handler(
    request: Request, exc: ValidationException
) -> Response:
    return Response(
        media_type=MediaType.TEXT,
        content=f"validation error: {exc.detail}",
        status_code=400,
    )


def internal_server_error_handler(request: Request, exc: Exception) -> Response:
    return Response(
        media_type=MediaType.TEXT,
        content=f"server error: {exc}",
        status_code=500,
    )


def value_error_handler(request: Request, exc: ValueError) -> Response:
    return Response(
        media_type=MediaType.TEXT,
        content=f"value error: {exc}",
        status_code=400,
    )


@get("/validation-error")
async def validation_error(some_query_param: str) -> str:
    return some_query_param


@get("/server-error")
async def server_error() -> None:
    raise HTTPException()


@get("/value-error")
async def value_error() -> None:
    raise ValueError("this is wrong")


app = Litestar(
    route_handlers=[validation_error, server_error, value_error],
    exception_handlers={
        ValidationException: validation_exception_handler,
        HTTP_500_INTERNAL_SERVER_ERROR: internal_server_error_handler,
        ValueError: value_error_handler,
    },
)


# run: /validation-error
# run: /server-error
# run: /value-error
