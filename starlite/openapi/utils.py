import re
from typing import List, Optional

from starlite.handlers.http import HTTPRouteHandler

CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")


def pascal_case_to_text(s: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'"""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, s)).strip()


def extract_tags_from_route_handler(route_handler: HTTPRouteHandler) -> Optional[List[str]]:
    """Extracts and combines tags from route_handler and any owners"""
    child_tags = route_handler.tags or []
    parent_tags = []
    if route_handler.owner and hasattr(route_handler.owner, "tags"):
        parent_tags = route_handler.owner.tags or []
    return list(set(child_tags) | set(parent_tags)) or None
