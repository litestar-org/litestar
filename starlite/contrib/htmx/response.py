from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, TypeVar, Union
from urllib.parse import quote

from starlite import MediaType, Request, Response, Starlite
from starlite.contrib.htmx.types import (
    EventAfterType,
    HtmxHeaderType,
    LocationType,
    PushUrlType,
    ReSwapMethod,
    TriggerEventType,
)
from starlite.contrib.htmx.utils import HTMX_STOP_POLLING, get_headers
from starlite.response_containers import Template
from starlite.status_codes import HTTP_200_OK

if TYPE_CHECKING:
    from starlite.response import TemplateResponse

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
        and pass redirect url.
        """
        super().__init__(content=None, headers=get_headers(hx_headers=HtmxHeaderType(redirect=redirect_to)))
        del self.headers["Location"]


class ClientRefresh(Response):
    """Response to support HTMX client page refresh"""

    def __init__(self) -> None:
        """Set Status code to 200 and set headers."""
        super().__init__(content=None, headers=get_headers(hx_headers=HtmxHeaderType(refresh=True)))


class PushUrl(Generic[T], Response[T]):
    """Response to push new url into the history stack."""

    def __init__(self, content: T, push_url: PushUrlType, **kwargs: Any) -> None:
        """Initialize PushUrl."""
        super().__init__(
            content=content,
            status_code=HTTP_200_OK,
            headers=get_headers(hx_headers=HtmxHeaderType(push_url=push_url)),
            **kwargs,
        )


class ReplaceUrl(Generic[T], Response[T]):
    """Response to replace url in the Browser Location bar."""

    def __init__(self, content: T, replace_url: PushUrlType, **kwargs: Any) -> None:
        """Initialize ReplaceUrl."""
        super().__init__(
            content=content,
            status_code=HTTP_200_OK,
            headers=get_headers(hx_headers=HtmxHeaderType(replace_url=replace_url)),
            **kwargs,
        )


class Reswap(Generic[T], Response[T]):
    """Response to specify how the response will be swapped."""

    def __init__(
        self,
        content: T,
        method: ReSwapMethod,
        **kwargs: Any,
    ) -> None:
        """Initialize Reswap."""
        super().__init__(content=content, headers=get_headers(hx_headers=HtmxHeaderType(re_swap=method)), **kwargs)


class Retarget(Generic[T], Response[T]):
    """Response to target different element on the page."""

    def __init__(self, content: T, target: str, **kwargs: Any) -> None:
        """Initialize Retarget."""
        super().__init__(content=content, headers=get_headers(hx_headers=HtmxHeaderType(re_target=target)), **kwargs)


class TriggerEvent(Generic[T], Response[T]):
    """Trigger Client side event."""

    def __init__(
        self,
        content: T,
        name: str,
        after: EventAfterType,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize TriggerEvent."""
        event = TriggerEventType(name=name, params=params, after=after)
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
        """Initialize HXLocation, Set status code to 200 (required by HTMX),
        and pass redirect url.
        """
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
    """Convenient type for returning HTMX Template responses."""

    push_url: Optional[PushUrlType] = None
    """This parameter accepts either a string value for url to push to browser history or
    boolean False to prevent HTMX client from pushing a url to browser history."""
    re_swap: ReSwapMethod = None
    """This parameter accepts either a string method value to instruct HTMX which swapping method to use."""
    re_target: Optional[str] = None
    """This parameter accepts string value for 'id of target element' to apply changes to."""
    trigger_event: Optional[str] = None
    """This parameter accepts string value of event name to trigger."""
    params: Optional[Dict[str, Any]] = None
    """This parameter accepts dictionary of parameters if any required with trigger event parameter."""
    after: Optional[EventAfterType] = None
    """This parameter accepts string value for changes to apply after 'receive', 'settle' or 'swap' event."""

    def to_response(
        self,
        headers: Dict[str, Any],
        media_type: Union["MediaType", str],
        status_code: int,
        app: "Starlite",
        request: "Request",
    ) -> "TemplateResponse":
        """Add HTMX headers and create TemplateResponse."""

        if self.trigger_event:
            event = TriggerEventType(name=str(self.trigger_event), params=self.params, after=self.after)
        else:
            event = None
        hx_headers: Dict[str, Any] = get_headers(
            hx_headers=HtmxHeaderType(
                push_url=self.push_url, re_swap=self.re_swap, re_target=self.re_target, trigger_event=event
            )
        )
        return super().to_response(
            headers=hx_headers, status_code=status_code, media_type=media_type, app=app, request=request
        )
