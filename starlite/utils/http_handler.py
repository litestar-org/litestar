from typing import Any


def is_http_handler(value: Any) -> bool:
    """Predicate that determines if a given value is an http handler function"""
    return callable(value) and hasattr(value, "route_info")
