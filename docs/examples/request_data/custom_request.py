from litestar import Litestar, Request, get
from litestar.connection.base import empty_receive, empty_send
from litestar.enums import HttpMethod
from litestar.types import Receive, Scope, Send

KITTEN_NAMES_MAP = {
    HttpMethod.DELETE: "Dziewczynka",
    HttpMethod.GET: "Pusia",
    HttpMethod.HEAD: "Nepomuk",
    HttpMethod.OPTIONS: "Boszko",
    HttpMethod.PATCH: "Morro",
    HttpMethod.POST: "Irinka",
    HttpMethod.PATCH: "Kotel",
}


class CustomRequest(Request):
    """Enrich request with the kitten name."""

    __slots__ = ("kitten_name",)

    def __init__(self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send) -> None:
        """Initialize CustomRequest class."""
        super().__init__(scope=scope, receive=receive, send=send)
        self.kitten_name = KITTEN_NAMES_MAP.get(scope["method"], "Kundzia")


@get(path="/kitten-name")
def get_kitten_name(request: CustomRequest) -> str:
    """Get kitten name based on the HTTP method."""
    return request.kitten_name


app = Litestar(
    route_handlers=[get_kitten_name],
    request_class=CustomRequest,
    debug=True,
)
