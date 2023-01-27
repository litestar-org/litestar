import json
from typing import Any, Dict, Literal, Optional, TypeVar
from urllib.parse import quote

from starlite import Response, Template
from starlite.status_codes import HTTP_200_OK

EventAfterType = Literal["receive", "settle", "swap"]

# HTMX defined HTTP status code.
# Response carrying this status code will ask client to stop Polling.
HTMX_STOP_POLLING = 286
T = TypeVar("T")


class HXStopPolling(Response):
    """Stop HTMX client from Polling."""

    def __init__(self) -> None:
        """Initialize"""
        super().__init__(content=None)
        self.status_code = HTMX_STOP_POLLING


class ClientRedirect(Response):
    """HTMX Response class to support client side redirect."""

    def __init__(self, url: str) -> None:
        """Set status code to 200 (required by HTMX),
        and pass redirect url
        """
        super().__init__(
            content=None,
            status_code=HTTP_200_OK,
            headers={"HX-Redirect": quote(url, safe="/#%[]=:;$&()+,!?*@'~"), "Location": ""},
        )
        del self.headers["Location"]


class ClientRefresh(Response):
    """Class to support HTMX client page refresh"""

    def __init__(self) -> None:
        """Set Status code to 200 and set headers."""
        super().__init__(content=None, status_code=HTTP_200_OK, headers={"HX-Refresh": "true"})


class PushUrl(Response):
    """Class to push new url into the history stack"""

    def __init__(self, content: Response[T], url: str = "", **kwargs: Any) -> None:
        """Initialize"""
        push = "false" if url == "" else url
        super().__init__(content=content, status_code=HTTP_200_OK, headers={"HX-Push-Url": push}, **kwargs)


class Reswap(Response):
    """Class to specify how the response will be swapped."""

    def __init__(
        self,
        content: Response[T],
        method: Literal[
            "innerHTML", "outerHTML", "beforebegin", "afterbegin", "beforeend", "afterend", "delete", "none"
        ],
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        super().__init__(content=content, headers={"HX-Reswap": method}, **kwargs)


class Retarget(Response):
    """Class to target different element on the page"""

    def __init__(self, content: Response[T], target: str, **kwargs: Any) -> None:
        """Initialize"""
        super().__init__(content=content, headers={"HX-Retarget": target}, **kwargs)


class TriggerEvent(Response):
    """Trigger Client side event"""

    def __init__(
        self,
        content: Response[T],
        name: str,
        after: EventAfterType,
        params: "Dict[str, Any] | None" = None,
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        params = params if params else {}
        if after == "receive":
            header = "HX-Trigger"
        elif after == "settle":
            header = "HX-Trigger-After-Settle"
        elif after == "swap":
            header = "HX-Trigger-After-Swap"
        else:
            raise ValueError("Invalid value for after param. Value must be either 'receive', 'settle' or 'swap'.")
        headers = {header: json.dumps({name: params})}
        super().__init__(content=content, headers=headers, **kwargs)


class HXLocation(Response):
    """Client side redirect without full page reload."""

    def __init__(
        self,
        redirect_to: str,
        source: Optional[str] = None,
        event: Optional[str] = None,
        target: Optional[str] = None,
        swap: Optional[
            Literal["innerHTML", "outerHTML", "beforebegin", "afterbegin", "beforeend", "afterend", "delete", "none"]
        ] = None,
        headers: Optional[Dict[str, Any]] = None,
        values: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        super().__init__(
            content=None,
            status_code=HTTP_200_OK,
            headers={"Location": quote(redirect_to, safe="/#%[]=:;$&()+,!?*@'~")},
            **kwargs,
        )
        spec: Dict[str, Any] = {}
        if self.headers:
            spec["path"] = self.headers.get("Location")
            del self.headers["Location"]

        if source is not None:
            spec["source"] = source
        if event is not None:
            spec["event"] = event
        if target is not None:
            spec["target"] = target
        if swap is not None:
            spec["swap"] = swap
        if headers is not None:
            spec["headers"] = headers
        if values is not None:
            spec["values"] = values
        self.headers["HX-Location"] = json.dumps(spec)


class HTMXTemplate(Template):
    """Send Template or Partial Template and push url to browser history stack"""

    def __init__(self, push: str = "", **kwargs: Any) -> None:
        """Initialize class"""
        url = push if push != "" else "false"
        super().__init__(headers={"HX-Push-Url": url}, **kwargs)
