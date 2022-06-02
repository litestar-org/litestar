import re
from typing import TYPE_CHECKING, List, Optional

from starlite.handlers.http import HTTPRouteHandler

if TYPE_CHECKING:
    from typing import Union

    from starlite import Controller, Router, Starlite


CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")


def pascal_case_to_text(s: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'"""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, s)).strip()


def extract_tags_from_route_handler(route_handler: HTTPRouteHandler) -> Optional[List[str]]:
    """Extracts and combines tags from route_handler and any owners"""
    child_tags = route_handler.tags or []
    parent_tags: List[str] = []
    obj: "Union[HTTPRouteHandler, Controller, Router, Starlite]"
    obj = route_handler
    while hasattr(obj, "owner"):
        if obj.owner is None:
            break
        obj = obj.owner
        parent_tags += getattr(obj, "tags", None) or []
    return list(set(child_tags) | set(parent_tags)) or None
