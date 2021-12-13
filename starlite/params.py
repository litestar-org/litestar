from typing import Optional

from starlette.requests import Request

from starlite.exceptions import ValidationException


class Header(str):
    def value_from_request(self, request: Request, allow_none: bool) -> Optional[str]:
        """
        Given a request object, return the headers value or raise an exception if None is not allowed
        """
        value = request.headers.get(self)
        if value or allow_none:
            return value
        raise ValidationException(
            detail=f"Missing header parameter {self}."
            f"\n\nIf this parameter is not required, define it with 'allow_none = True'."
        )
