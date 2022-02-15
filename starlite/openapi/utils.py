import re
from typing import List, Optional

from starlite.handlers.http import HTTPRouteHandler

CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")


def pascal_case_to_text(s: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'"""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, s)).strip()


def extract_tags_from_route_handler(route_handler: HTTPRouteHandler) -> Optional[List[str]]:
    child_tags = set(route_handler.tags or [])
    parent_tags = set(route_handler.owner.tags if route_handler.owner and hasattr(route_handler.owner, "tags") else [])
    return list(child_tags | parent_tags) or None
