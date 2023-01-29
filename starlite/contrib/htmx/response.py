from typing import Any, Dict, Generic, Literal, Optional, TypeVar
from urllib.parse import quote

from starlite import Response, Template
from starlite.contrib.htmx.utils import HTMX_STOP_POLLING, HX
from starlite.status_codes import HTTP_200_OK
from starlite.utils import encode_json

EventAfterType = Literal["receive", "settle", "swap"]
ReSwapMethod = Literal[
    "innerHTML", "outerHTML", "beforebegin", "afterbegin", "beforeend", "afterend", "delete", "none", None
]
# HTMX defined HTTP status code.
# Response carrying this status code will ask client to stop Polling.
T = TypeVar("T")


class HXStopPolling(Response):
    """Stop HTMX client from Polling."""

    def __init__(self) -> None:
        """Initialize"""
        super().__init__(content=None)
        self.status_code = HTMX_STOP_POLLING


class ClientRedirect(Response):
    """HTMX Response class to support client side redirect."""

    def __init__(self, redirect_to: str) -> None:
        """Set status code to 200 (required by HTMX),
        and pass redirect url
        """
        super().__init__(
            content=None,
            status_code=HTTP_200_OK,
            headers={HX.REDIRECT: quote(redirect_to, safe="/#%[]=:;$&()+,!?*@'~"), "Location": ""},
        )
        del self.headers["Location"]


class ClientRefresh(Response):
    """Class to support HTMX client page refresh"""

    def __init__(self) -> None:
        """Set Status code to 200 and set headers."""
        super().__init__(content=None, status_code=HTTP_200_OK, headers={HX.REFRESH: "true"})


class PushUrl(Generic[T], Response[T]):
    """Class to push new url into the history stack"""

    def __init__(self, content: T, push: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize"""
        push_url = push if push else "false"
        super().__init__(content=content, status_code=HTTP_200_OK, headers={HX.PUSH_URL: push_url}, **kwargs)


class Reswap(Generic[T], Response[T]):
    """Class to specify how the response will be swapped."""

    def __init__(
        self,
        content: T,
        method: ReSwapMethod,
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        super().__init__(content=content, headers={HX.RE_SWAP: method}, **kwargs)


class Retarget(Generic[T], Response[T]):
    """Class to target different element on the page"""

    def __init__(self, content: T, target: str, **kwargs: Any) -> None:
        """Initialize"""
        super().__init__(content=content, headers={HX.RE_TARGET: target}, **kwargs)


class TriggerEvent(Generic[T], Response[T]):
    """Trigger Client side event"""

    def __init__(
        self,
        content: T,
        name: str,
        after: EventAfterType,
        params: "Dict[str, Any] | None" = None,
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        header: str
        params = params if params else {}
        if after == "receive":
            header = HX.TRIGGER_EVENT.value
        elif after == "settle":
            header = HX.TRIGGER_AFTER_SETTLE.value
        elif after == "swap":
            header = HX.TRIGGER_AFTER_SWAP.value
        else:
            raise ValueError("Invalid value for after param. Value must be either 'receive', 'settle' or 'swap'.")
        headers = {header: encode_json({name: params}).decode()}
        super().__init__(content=content, headers=headers, **kwargs)


class HXLocation(Response):
    """Client side redirect without full page reload."""

    def __init__(
        self,
        redirect_to: str,
        source: Optional[str] = None,
        event: Optional[str] = None,
        target: Optional[str] = None,
        swap: ReSwapMethod = None,
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
        self.headers[HX.LOCATION] = encode_json(spec).decode()


class HTMXTemplate(Template):
    """Send Template or Partial Template and push url to browser history stack"""

    def __init__(self, push: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize class"""
        url = push if push else "false"
        super().__init__(headers={HX.PUSH_URL: url}, **kwargs)
