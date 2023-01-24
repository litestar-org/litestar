import json
from typing import Any, Literal
from urllib.parse import quote

from starlite import Response, Template
from starlite.status_codes import HTTP_200_OK

EventAfterType = Literal["receive", "settle", "swap"]

# HTMX defined HTTP status code.
# Response carrying this status code will ask client to stop Polling.
HTMX_STOP_POLLING = 286


class HXStopPolling(Response):
    """Stop HTMX client from Polling."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize"""
        super().__init__(*args, **kwargs)
        self.status_code = HTMX_STOP_POLLING


class ClientRedirect(Response):
    """HTMX Response class to support client side redirect."""

    def __init__(self, url: str, **kwargs: Any) -> None:
        """Set status code to 200 (required by HTMX),
        and pass redirect url
        """
        super().__init__(
            content=None,
            status_code=HTTP_200_OK,
            headers={"HX-Redirect": quote(url, safe="/#%[]=:;$&()+,!?*@'~"), "Location": ""},
            **kwargs,
        )


class ClientRefresh(Response):
    """Class to support HTMX client page refresh"""

    def __init__(self, **kwargs: Any) -> None:
        """Set Status code to 200 and set headers."""
        super().__init__(content=None, status_code=HTTP_200_OK, headers={"HX-Refresh": "true"}, **kwargs)


class PushUrl(Response):
    """Class to push new url into the history stack"""

    def __init__(self, url: str = "") -> None:
        """Initialize"""
        push = "false" if url == "" else url
        super().__init__(content=None, status_code=200, headers={"HX-Push-Url": push})


class HtmxTemplateResponse(Template):
    """Send Template or Partial Template and push url to browser history stack"""

    def __init__(self, push: str = "", **kwargs: Any) -> None:
        """Initialize class"""
        url = "false" if push == "" else push
        super().__init__(headers={"HX-Push-Url": url}, **kwargs)


class Reswap(Response):
    """Class to specify how the response will be swapped."""

    def __init__(
        self,
        method: Literal[
            "innerHTML", "outerHTML", "beforebegin", "afterbegin", "beforeend", "afterend", "delete", "none"
        ],
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        super().__init__(content=None, headers={"HX-Reswap": method}, **kwargs)


class Retarget(Response):
    """Class to target different element on the page"""

    def __init__(self, target: str) -> None:
        """Initialize"""
        super().__init__(self, headers={"HX-Retarget": target})


class TriggerEvent(Response):
    """Trigger Client side event"""

    def __init__(
        self, name: str, params: dict[str, Any] | None = None, *, after: EventAfterType = "receive", **kwargs: Any
    ) -> None:
        """Initialize"""
        params = params or {}
        header = "HX-Trigger"
        if after == "settle":
            header += "-After-Settle"
        elif after == "swap":
            header += "-After-Swap"
        else:
            raise ValueError("Value for 'after' must be one of: 'receive', 'settle', or 'swap'.")
        headers = {header: json.dumps({name: params})}
        super().__init__(content=None, headers=headers, **kwargs)


class HXLocation(Response):
    """Client side redirect without full page reload."""

    def __init__(
        self,
        redirect_to: str,
        source: str | None = None,
        event: str | None = None,
        target: str | None = None,
        swap: Literal[
            "innerHTML",
            "outerHTML",
            "beforebegin",
            "afterbegin",
            "beforeend",
            "afterend",
            "delete",
            "none",
            None,
        ] = None,
        headers: dict[str, Any] | None = None,
        values: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        super().__init__(
            content=None,
            status_code=HTTP_200_OK,
            headers={"Location": quote(redirect_to, safe="/#%[]=:;$&()+,!?*@'~")},
            **kwargs,
        )
        spec: dict[str, Any] = {}
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
