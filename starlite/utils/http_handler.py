from typing import Any, Callable, Optional

from starlite.decorators import RouteInfo


def is_http_handler(value: Any) -> bool:
    """Predicate that determines if a given value is an http handler function"""
    return callable(value) and hasattr(value, "route_info")


def extract_route_info(value: Callable) -> Optional[RouteInfo]:
    """Helper to retrieve the route info model from a callable, if present"""
    return getattr(value, "route_info") if is_http_handler(value) else None
