from litestar import Litestar, MediaType, Request, Response, get
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR


def plain_text_exception_handler(_: Request, exc: Exception) -> Response:
    """Default handler for exceptions subclassed from HTTPException."""
    status_code = getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exc, "detail", "")

    return Response(
        media_type=MediaType.TEXT,
        content=detail,
        status_code=status_code,
    )


@get("/")
async def index() -> None:
    raise HTTPException(detail="an error occurred", status_code=400)


app = Litestar(
    route_handlers=[index],
    exception_handlers={HTTPException: plain_text_exception_handler},
)

# run: /
