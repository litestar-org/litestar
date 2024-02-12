from typing import Optional

from pydantic import BaseModel

import litestar.status_codes
from litestar import Litestar, get


class ProblemDetails(BaseModel):
    title: str
    type: str
    status: Optional[int] = None
    detail: Optional[str] = None
    instance: Optional[str] = None


@get("/resources", status_code=litestar.status_codes.HTTP_418_IM_A_TEAPOT, media_type="application/problem+json")
async def retrieve_resource() -> ProblemDetails:
    return ProblemDetails(
        title="Server thinks it is a teapot",
        type="Server delusion",
        status=litestar.status_codes.HTTP_418_IM_A_TEAPOT,
    )


app = Litestar(route_handlers=[retrieve_resource])
