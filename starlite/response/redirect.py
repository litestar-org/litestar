from typing import TYPE_CHECKING, Any, Dict, Optional, Union
from urllib.parse import quote

from starlite.enums import MediaType
from starlite.response.base import Response
from starlite.status_codes import HTTP_307_TEMPORARY_REDIRECT

if TYPE_CHECKING:
    from typing_extensions import Literal

    from starlite.datastructures import BackgroundTask, BackgroundTasks
    from starlite.types import ResponseCookies


class RedirectResponse(Response[Any]):
    def __init__(
        self,
        url: str,
        *,
        background: Optional[Union["BackgroundTask", "BackgroundTasks"]] = None,
        status_code: "Literal[301, 302, 303, 307, 308]" = HTTP_307_TEMPORARY_REDIRECT,
        headers: Optional[Dict[str, Any]] = None,
        cookies: Optional["ResponseCookies"] = None,
    ) -> None:
        super().__init__(
            background=background,
            content=b"",
            cookies=cookies,
            headers={**(headers or {}), "location": quote(url, safe="/#%[]=:;$&()+,!?*@'~")},
            media_type=MediaType.TEXT,
            status_code=status_code,
        )
