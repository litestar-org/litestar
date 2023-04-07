from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from urllib.parse import quote

from litestar import Litestar, MediaType, Request, Response
from litestar.contrib.htmx._utils import HTMX_STOP_POLLING, get_headers
from litestar.contrib.htmx.types import (
    EventAfterType,
    HtmxHeaderType,
    LocationType,
    PushUrlType,
    ReSwapMethod,
    TriggerEventType,
)
from litestar.response import TemplateResponse
from litestar.response_containers import ResponseContainer, Template
from litestar.status_codes import HTTP_200_OK

__all__ = (
    "ClientRedirect",
    "ClientRefresh",
    "HTMXTemplate",
    "HXLocation",
    "HXStopPolling",
    "PushUrl",
    "ReplaceUrl",
    "Reswap",
    "Retarget",
    "TriggerEvent",
)

if TYPE_CHECKING:
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.datastructures import Cookie


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
        """Set status code to 200 (required by HTMX), and pass redirect url."""
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
        params: dict[str, Any] | None = None,
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
        source: str | None = None,
        event: str | None = None,
        target: str | None = None,
        swap: ReSwapMethod = None,
        hx_headers: dict[str, Any] | None = None,
        values: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize HXLocation, Set status code to 200 (required by HTMX),
        and pass redirect url.
        """
        super().__init__(
            content=None,
            headers={"Location": quote(redirect_to, safe="/#%[]=:;$&()+,!?*@'~")},
            **kwargs,
        )
        spec: dict[str, Any] = get_headers(
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


@dataclass
class HTMXTemplate(ResponseContainer[TemplateResponse]):
    """HTMX template wrapper"""

    name: str
    """Path-like name for the template to be rendered, e.g. "index.html"."""
    context: dict[str, Any] = field(default_factory=dict)
    """A dictionary of key/value pairs to be passed to the temple engine's render method.

    Defaults to None.
    """
    background: BackgroundTask | BackgroundTasks | None = field(default=None)
    """A :class:`BackgroundTask <.background_tasks.BackgroundTask>` instance or
    :class:`BackgroundTasks <.background_tasks.BackgroundTasks>` to execute after the response is finished. Defaults to
    ``None``.
    """
    headers: dict[str, Any] = field(default_factory=dict)
    """A string/string dictionary of response headers.Header keys are insensitive. Defaults to ``None``."""
    cookies: list[Cookie] = field(default_factory=list)
    """A list of :class:`Cookies <.datastructures.Cookie>` to be set under the response ``Set-Cookie`` header. Defaults
    to ``None``.
    """
    media_type: MediaType | str | None = field(default=None)
    """If defined, overrides the media type configured in the route decorator."""
    encoding: str = field(default="utf-8")
    """The encoding to be used for the response headers."""
    push_url: PushUrlType | None = field(default=None)
    """Either a string value specifying a URL to push to browser history or ``False`` to prevent HTMX client from
    pushing a url to browser history."""
    re_swap: ReSwapMethod | None = field(default=None)
    """Method value to instruct HTMX which swapping method to use."""
    re_target: str | None = field(default=None)
    """Value for 'id of target element' to apply changes to."""
    trigger_event: str | None = field(default=None)
    """Event name to trigger."""
    params: dict[str, Any] | None = field(default=None)
    """Dictionary of parameters if any required with trigger event parameter."""
    after: EventAfterType | None = field(default=None)
    """Changes to apply after ``receive``, ``settle`` or ``swap`` event."""

    def to_response(
        self,
        headers: dict[str, Any],
        media_type: MediaType | str,
        status_code: int,
        app: Litestar,
        request: Request,
    ) -> TemplateResponse:
        """Add HTMX headers and return a :class:`TemplateResponse <.response.TemplateResponse>`."""

        event: TriggerEventType | None = None
        if self.trigger_event:
            event = TriggerEventType(name=str(self.trigger_event), params=self.params, after=self.after)

        hx_headers: dict[str, Any] = get_headers(
            hx_headers=HtmxHeaderType(
                push_url=self.push_url, re_swap=self.re_swap, re_target=self.re_target, trigger_event=event
            )
        )

        template = Template(
            name=self.name,
            background=self.background,
            encoding=self.encoding,
        )

        return template.to_response(
            headers=hx_headers, media_type=media_type, app=app, status_code=status_code, request=request
        )
