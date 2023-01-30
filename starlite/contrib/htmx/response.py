from typing import Any, Dict, Generic, Optional, TypeVar
from urllib.parse import quote

from starlite import Response, Template
from starlite.contrib.htmx.types import (
    EventAfterType,
    HtmxHeaderType,
    LocationType,
    PushUrlType,
    ReSwapMethod,
    TriggerEventType,
)
from starlite.contrib.htmx.utils import HTMX_STOP_POLLING, get_headers
from starlite.status_codes import HTTP_200_OK

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
            headers=get_headers(hx_headers=HtmxHeaderType(redirect=redirect_to)),
        )
        del self.headers["Location"]


class ClientRefresh(Response):
    """Class to support HTMX client page refresh"""

    def __init__(self) -> None:
        """Set Status code to 200 and set headers."""
        super().__init__(
            content=None, status_code=HTTP_200_OK, headers=get_headers(hx_headers=HtmxHeaderType(refresh=True))
        )


class PushUrl(Generic[T], Response[T]):
    """Class to push new url into the history stack"""

    def __init__(self, content: T, push_url: Optional[PushUrlType] = None, **kwargs: Any) -> None:
        """Initialize"""
        if push_url is None:
            raise ValueError("Enter url to push to the Browser History.")
        super().__init__(
            content=content,
            status_code=HTTP_200_OK,
            headers=get_headers(hx_headers=HtmxHeaderType(push_url=push_url)),
            **kwargs,
        )


class Reswap(Generic[T], Response[T]):
    """Class to specify how the response will be swapped."""

    def __init__(
        self,
        content: T,
        method: ReSwapMethod,
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        super().__init__(content=content, headers=get_headers(hx_headers=HtmxHeaderType(re_swap=method)), **kwargs)


class Retarget(Generic[T], Response[T]):
    """Class to target different element on the page"""

    def __init__(self, content: T, target: str, **kwargs: Any) -> None:
        """Initialize"""
        super().__init__(content=content, headers=get_headers(hx_headers=HtmxHeaderType(re_target=target)), **kwargs)


class TriggerEvent(Generic[T], Response[T]):
    """Trigger Client side event"""

    def __init__(
        self,
        content: T,
        name: str,
        after: EventAfterType,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize"""
        event = TriggerEventType(name=name, params=params, after=after)
        # if params:
        #     event['params'] = params

        headers = get_headers(hx_headers=HtmxHeaderType(trigger_event=event))
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
        hx_headers: Optional[Dict[str, Any]] = None,
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
        spec: Dict[str, Any] = get_headers(
            hx_headers=HtmxHeaderType(
                location=LocationType(
                    path=str(self.headers.get("Location")),
                    source=source,
                    event=event,
                    target=target,
                    swap=swap,
                    values=values,
                    hx_headers=hx_headers,
                )
            )
        )
        del self.headers["Location"]
        self.headers.update(spec)


class HTMXTemplate(Template):
    """Send Template or Partial Template and push url to browser history stack"""

    def __init__(
        self,
        push_url: Optional[PushUrlType] = None,
        re_swap: ReSwapMethod = None,
        re_target: Optional[str] = None,
        trigger_event: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        after: Optional[EventAfterType] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize class"""
        event = TriggerEventType(name=str(trigger_event), params=params, after=after) if trigger_event else None
        hx_headers: Dict[str, Any] = get_headers(
            hx_headers=HtmxHeaderType(push_url=push_url, re_swap=re_swap, re_target=re_target, trigger_event=event)
        )
        super().__init__(headers=hx_headers, **kwargs)
