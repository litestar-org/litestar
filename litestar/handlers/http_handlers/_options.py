from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from litestar.constants import DEFAULT_ALLOWED_CORS_HEADERS
from litestar.datastructures import Headers
from litestar.enums import HttpMethod, MediaType
from litestar.handlers import HTTPRouteHandler
from litestar.response import Response
from litestar.status_codes import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST

if TYPE_CHECKING:
    from litestar.types import Method, Scope


def create_options_handler(path: str, allow_methods: Iterable[Method]) -> HTTPRouteHandler:
    """Args:
        path: The route path

    Returns:
        An HTTP route handler for OPTIONS requests.
    """

    def options_handler() -> Response:
        """Handler function for OPTIONS requests.

        Returns:
            Response
        """
        return Response(
            content=None,
            status_code=HTTP_204_NO_CONTENT,
            headers={"Allow": ", ".join(sorted(allow_methods))},  # pyright: ignore
            media_type=MediaType.TEXT,
        )

    return HTTPRouteHandler(
        path=path,
        http_method=[HttpMethod.OPTIONS],
        include_in_schema=False,
        sync_to_thread=False,
    )(options_handler)
