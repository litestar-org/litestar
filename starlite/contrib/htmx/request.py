from functools import cached_property
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import unquote, urlsplit, urlunsplit

from starlite import Request
from starlite.contrib.htmx.utils import HTMXHeaders
from starlite.exceptions import SerializationException
from starlite.utils import decode_json

if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


class HtmxDetails:
    """HtmxDetails holds all the values sent by HTMX client in headers
    and provide convenient properties.
    """

    def __init__(self, request: Request) -> None:
        """Initialize Class"""
        self.request = request

    def _get_header_value(self, name: str) -> Optional[str]:
        """Parse request header
        Checks for uri encoded header and unquotes it in readable format.
        """
        value = self.request.headers.get(name) or None
        if value and self.request.headers.get(name + "-URI-AutoEncoded") == "true":
            return unquote(value)
        return value

    def __bool__(self) -> bool:
        """Allow to check whether request is sent by a HTMX client."""
        return self._get_header_value(HTMXHeaders.REQUEST) == "true"

    @cached_property
    def boosted(self) -> bool:
        """Allow to check whether request is boosted."""
        return self._get_header_value(HTMXHeaders.BOOSTED) == "true"

    @cached_property
    def current_url(self) -> Optional[str]:
        """Current url value sent by HTMX client. Helps in tracking navigation history."""
        return self._get_header_value(HTMXHeaders.CURRENT_URL)

    @cached_property
    def current_url_abs_path(self) -> Optional[str]:
        """Current url abs path value, to get query and path parameter sent by HTMX client."""
        url = self.current_url
        if url is not None:
            split = urlsplit(url)
            if split.scheme == self.request.scope["scheme"] and split.netloc == self.request.headers.get("host"):
                return urlunsplit(split._replace(scheme="", netloc=""))
            return None
        return url

    @cached_property
    def history_restore_request(self) -> bool:
        """If True then, request is for history restoration after a miss in the local history cache"""
        return self._get_header_value(HTMXHeaders.HISTORY_RESTORE_REQUEST) == "true"

    @cached_property
    def prompt(self) -> Optional[str]:
        """User Response to prompt.
        <button hx-delete="/account" hx-prompt="Enter your account name to confirm deletion">
            Delete My Account
        </button>
        """
        return self._get_header_value(HTMXHeaders.PROMPT)

    @cached_property
    def target(self) -> Optional[str]:
        """The id of the target element if it exists"""
        return self._get_header_value(HTMXHeaders.TARGET)

    @cached_property
    def trigger(self) -> Optional[str]:
        """The id of the triggered element if it exists"""
        return self._get_header_value(HTMXHeaders.TRIGGER_ID)

    @cached_property
    def trigger_name(self) -> Optional[str]:
        """The name of the triggered element if it exists"""
        return self._get_header_value(HTMXHeaders.TRIGGER_NAME)

    @cached_property
    def triggering_event(self) -> Any:
        """The name of the triggered event.
        'event-header' extension adds the Triggering-Event header to requests.
        """
        value = self._get_header_value(HTMXHeaders.TRIGGERING_EVENT)
        if value is not None:
            try:
                value = decode_json(value)
            except SerializationException:
                value = None
        return value


class HTMXRequest(Request):
    """HTMX Request class to work with HTMX client"""

    __slots__ = ("htmx",)

    def __init__(self, scope: "Scope", receive: "Receive", send: "Send"):
        """Initialize Request"""
        super().__init__(scope=scope, receive=receive, send=send)
        self.htmx = HtmxDetails(self)
