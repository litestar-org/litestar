import re
from typing import cast

from starlite.enums import MediaType
from starlite.handlers import RouteHandler

CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")


def pascal_case_to_text(s: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'"""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, s)).strip()


def get_media_type(route_handler: RouteHandler) -> MediaType:
    """
    Return a MediaType enum member for the given RouteHandler or a default value
    """
    if route_handler.media_type:
        return cast(MediaType, route_handler.media_type)
    if route_handler.response_class and route_handler.response_class.media_type:
        return cast(MediaType, route_handler.response_class.media_type)
    return MediaType.JSON
