from typing import Any

from starlite.exceptions.base_exceptions import StarLiteException
from starlite.status_codes import WS_1000_NORMAL_CLOSURE


class WebSocketException(StarLiteException):
    """Exception class for websocket related events."""

    code: int
    """Exception code.

    Should be a number in the 4000+ range.
    """

    def __init__(self, *args: Any, detail: str, code: int = 4500) -> None:
        """Initialize `WebSocketException`.

        Args:
            *args: Any exception args.
            detail: Exception details.
            code: Exception code. Should be a number in the >= 1000.
        """
        super().__init__(*args, detail=detail)
        self.code = code


class WebSocketDisconnect(WebSocketException):
    """Exception class for websocket disconnect events."""

    def __init__(self, *args: Any, detail: str, code: int = WS_1000_NORMAL_CLOSURE) -> None:
        """Initialize `WebSocketDisconnect`.

        Args:
            *args: Any exception args.
            detail: Exception details.
            code: Exception code. Should be a number in the >= 1000.
        """
        super().__init__(*args, detail=detail, code=code)
