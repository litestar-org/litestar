from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict
from urllib.parse import quote

from starlite.utils import encode_json

if TYPE_CHECKING:
    from starlite.contrib.htmx.types import (
        EventAfterType,
        HtmxHeaderType,
        LocationType,
        ReSwapMethod,
        TriggerEventType,
    )

HTMX_STOP_POLLING = 286


class HX(str, Enum):
    """An Enum for HTMX Headers"""

    REDIRECT = "HX-Redirect"
    REFRESH = "HX-Refresh"
    PUSH_URL = "HX-Push-Url"
    REPLACE_URL = "HX-Replace-Url"
    RE_SWAP = "HX-Reswap"
    RE_TARGET = "HX-Retarget"
    LOCATION = "HX-Location"

    TRIGGER_EVENT = "HX-Trigger"
    TRIGGER_AFTER_SETTLE = "HX-Trigger-After-Settle"
    TRIGGER_AFTER_SWAP = "HX-Trigger-After-Swap"

    REQUEST = "HX-Request"
    BOOSTED = "HX-Boosted"
    CURRENT_URL = "HX-Current-URL"
    HISTORY_RESTORE_REQUEST = "HX-History-Restore-Request"
    PROMPT = "HX-Prompt"
    TARGET = "HX-Target"
    TRIGGER_ID = "HX-Trigger"
    TRIGGER_NAME = "HX-Trigger-Name"
    TRIGGERING_EVENT = "Triggering-Event"


def get_trigger_event_headers(trigger_event: "TriggerEventType") -> Dict[str, Any]:
    """Return headers for trigger event response."""
    params = trigger_event["params"] or {}
    after_params: Dict[EventAfterType, str] = {
        "receive": HX.TRIGGER_EVENT.value,
        "settle": HX.TRIGGER_AFTER_SETTLE.value,
        "swap": HX.TRIGGER_AFTER_SWAP.value,
    }
    trigger_header = after_params.get(trigger_event["after"])
    if trigger_header is None:
        raise ValueError("Invalid value for after param. Value must be either 'receive', 'settle' or 'swap'.")
    val = encode_json({trigger_event["name"]: params}).decode()
    return {trigger_header: val}


def get_redirect_header(url: str) -> Dict[str, Any]:
    """Return headers for redirect response."""
    return {HX.REDIRECT.value: quote(url, safe="/#%[]=:;$&()+,!?*@'~"), "Location": ""}


def get_push_url_header(url: str) -> Dict[str, Any]:
    """Return headers for push url to browser history response."""
    return {HX.PUSH_URL.value: url if url else "false"}


def get_replace_url_header(url: str) -> Dict[str, Any]:
    """Return headers for replace url in browser tab response."""
    return {HX.REPLACE_URL: url if url else "false"}


def get_refresh_header(refresh: bool) -> Dict[str, Any]:
    """Return headers for client refresh response."""
    value = ""
    if refresh:
        value = "true"
    return {HX.REFRESH.value: value}


def get_reswap_header(method: "ReSwapMethod") -> Dict[str, Any]:
    """Return headers for change swap method response."""
    return {HX.RE_SWAP.value: method}


def get_retarget_header(target: str) -> Dict[str, Any]:
    """Return headers for change target element response."""
    return {HX.RE_TARGET.value: target}


def get_location_headers(location: "LocationType") -> Dict[str, Any]:
    """Return headers for redirect without page-reload response."""
    spec: Dict[str, Any] = {}
    for key, value in location.items():
        if value:
            spec[key] = value
    if not spec:
        raise ValueError("redirect_to is required parameter.")
    return {HX.LOCATION.value: encode_json(spec).decode()}


def get_headers(hx_headers: "HtmxHeaderType") -> Dict[str, Any]:
    """Return headers for HTMX responses."""
    if not hx_headers:
        raise ValueError("Value for hx_headers cannot be None.")
    htmx_headers_dict: Dict[str, Callable] = {
        "redirect": get_redirect_header,
        "refresh": get_refresh_header,
        "push_url": get_push_url_header,
        "replace_url": get_replace_url_header,
        "re_swap": get_reswap_header,
        "re_target": get_retarget_header,
        "trigger_event": get_trigger_event_headers,
        "location": get_location_headers,
    }

    header: Dict[str, Any] = {}
    response: Dict[str, Any]
    key: str
    value: Any
    for key, value in hx_headers.items():
        if key in ["redirect", "refresh", "location", "replace_url"]:
            response = htmx_headers_dict[key](value)
            return response
        if value is not None:
            response = htmx_headers_dict[key](value)
            header.update(response)
    return header
