import re
from typing import TYPE_CHECKING, List, Optional, Pattern, Union

from starlite.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:

    from starlite.types import Scope, Scopes


def build_exclude_path_pattern(*, exclude: Optional[Union[str, List[str]]] = None) -> Optional[Pattern]:
    """Build single path pattern from list of patterns to opt-out from middleware processing.

    Args:
        exclude: A pattern or a list of patterns.

    Returns:
        An optional pattern to match against scope["path"] to opt-out from middleware processing.
    """
    if exclude is None:
        return None

    try:
        return re.compile("|".join(exclude)) if isinstance(exclude, list) else re.compile(exclude)
    except re.error as e:
        raise ImproperlyConfiguredException(
            "Unable to compile exclude patterns for middleware. Please make sure you passed a valid regular expression."
        ) from e


def should_bypass_middleware(
    *,
    scope: "Scope",
    scopes: "Scopes",
    exclude_opt_key: Optional[str] = None,
    exclude_path_pattern: Optional[Pattern] = None,
) -> bool:
    """Determine weather a middleware should be bypassed.

    Args:
        scope: The ASGI scope.
        scopes: A set with the ASGI scope types that are supported by the middleware.
        exclude_opt_key: Key in `opt` with which a route handler can "opt-out" of a middleware.
        exclude_path_pattern: If this pattern matches scope["path"], the middleware should
            be bypassed.

    Returns:
        A boolean indicating if a middleware should be bypassed
    """
    if scope["type"] not in scopes:
        return True

    if exclude_opt_key and scope["route_handler"].opt.get(exclude_opt_key):
        return True

    if exclude_path_pattern and exclude_path_pattern.findall(
        scope["path"] if not getattr(scope.get("route_handler", {}), "is_mount", False) else scope["raw_path"].decode()
    ):
        return True
    return False
