import logging
from typing import TYPE_CHECKING

from litestar import Litestar, get
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_400_BAD_REQUEST

logger = logging.getLogger()

if TYPE_CHECKING:
    from litestar.types import Scope


@get("/some-path", sync_to_thread=False)
def my_handler() -> None:
    """Route handler that raises an exception."""
    raise HTTPException(detail="bad request", status_code=HTTP_400_BAD_REQUEST)


async def after_exception_handler(exc: Exception, scope: "Scope") -> None:
    """Hook function that will be invoked after each exception."""
    state = scope["app"].state
    if not hasattr(state, "error_count"):
        state.error_count = 1
    else:
        state.error_count += 1

    logger.info(
        "an exception of type %s has occurred for requested path %s and the application error count is %d.",
        type(exc).__name__,
        scope["path"],
        state.error_count,
    )


app = Litestar([my_handler], after_exception=[after_exception_handler])
