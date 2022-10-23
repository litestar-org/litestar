from typing import Any

from starlite.exceptions.base_exceptions import StarLiteException
from starlite.status_codes import WS_1000_NORMAL_CLOSURE


class WebSocketException(StarLiteException):
    code: int
    """Exception code. Should be a number in the 4000+ range."""

    def __init__(self, *args: Any, detail: str, code: int = 4500) -> None:
        """Exception class for websocket related events.

        Args:
            *args: Any exception args.
            detail: Exception details.
            code: Exception code. Should be a number in the >= 1000.
        """
        super().__init__(*args, detail=detail)
        self.code = code


class WebSocketDisconnect(WebSocketException):
    def __init__(self, *args: Any, detail: str, code: int = WS_1000_NORMAL_CLOSURE) -> None:
        """Exception class for websocket disconnect events.

        Args:
            *args: Any exception args.
            detail: Exception details.
            code: Exception code. Should be a number in the >= 1000.
        """
        super().__init__(*args, detail=detail, code=code)
