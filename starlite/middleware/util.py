from typing import TYPE_CHECKING, Collection, Optional, Pattern

if TYPE_CHECKING:
    from starlite.types import Scope


def should_bypass_middleware(
    *,
    scope: "Scope",
    scopes: Collection[str],
    exclude_opt_key: Optional[str] = None,
    exclude_path_pattern: Optional[Pattern] = None
) -> bool:
    """Determine weather a middleware should be bypassed.

    Args:
        scope: Current scope
        scopes: Scopes the middleware should be used for
        exclude_opt_key: Key in `opt` with which a route handler can opt-out of a middleware
        exclude_path_pattern: If this pattern matches scope["pass"], the middleware should
            be bypassed

    Returns:
        A boolean indicating if a middleware should be bypassed
    """
    if scope["type"] not in scopes:
        return True
    if exclude_opt_key and scope["route_handler"].opt.get(exclude_opt_key):
        return True
    if exclude_path_pattern and exclude_path_pattern.findall(scope["path"]):
        return True
    return False
