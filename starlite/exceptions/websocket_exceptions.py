from typing import Any

from starlite.exceptions.base_exceptions import StarLiteException


class WebSocketException(StarLiteException):
    code: int
    """Exception code. Should be a number in the 4000+ range."""

    def __init__(self, *args: Any, detail: str, code: int = 4500) -> None:
        """Exception class for websocket related events.

        Args:
            *args: Any exception args.
            detail:
            code: Exception code. Should be a number in the 4000+ range.
        """
        super().__init__(*args, detail=detail)
        self.code = code
