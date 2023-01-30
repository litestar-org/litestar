from typing import Any, Dict, Literal, Optional, TypedDict, Union

from typing_extensions import Required

EventAfterType = Literal["receive", "settle", "swap", None]

PushUrlType = Union[str, Literal[False]]

ReSwapMethod = Literal[
    "innerHTML", "outerHTML", "beforebegin", "afterbegin", "beforeend", "afterend", "delete", "none", None
]


class LocationType(TypedDict):
    """Type for HX-Location header."""

    path: Required[str]
    source: Optional[str]
    event: Optional[str]
    target: Optional[str]
    swap: Optional[ReSwapMethod]
    values: Optional[Dict[str, str]]
    hx_headers: Optional[Dict[str, Any]]


class TriggerEventType(TypedDict):
    """Type for HX-Trigger header."""

    name: Required[str]
    params: Optional[Dict[str, Any]]
    after: Optional[EventAfterType]


class HtmxHeaderType(TypedDict, total=False):
    """Type for hx_headers parameter in get_headers()."""

    location: Optional[LocationType]
    redirect: Optional[str]
    refresh: bool
    push_url: Optional[PushUrlType]
    replace_url: Optional[PushUrlType]
    re_swap: Optional[ReSwapMethod]
    re_target: Optional[str]
    trigger_event: Optional[TriggerEventType]
