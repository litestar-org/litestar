from typing import Optional

from starlette.requests import Request

from starlite.exceptions import ValidationException


class Header(str):
    __slots__ = ("key", "allow_none")

    def __init__(self, key: str, allow_none: bool = False):
        super().__init__()
        self.key = key.lower()
        self.allow_none = allow_none

    def __call__(self, request: Request) -> Optional[str]:
        value = request.headers.get(self.key)
        if value or self.allow_none:
            return value
        raise ValidationException(
            detail=f"Missing header parameter {self.key}."
            f"\n\nIf this parameter is not required, define it with 'allow_none = True'."
        )
