from typing import Any

from starlite.utils import warn_deprecation

from .base import SessionMiddleware


def __getattr__(name: str) -> Any:
    """Provide lazy importing as per https://peps.python.org/pep-0562/"""

    if name != "SessionCookieConfig":
        raise AttributeError(f"Module {__package__} has no attribute {name}")

    from .cookie_backend import CookieBackendConfig

    warn_deprecation(
        deprecated_name=f"{name} from {__package__}",
        kind="import",
        alternative="'from startlite.middleware.sessions.cookie_backend import CookieBackendConfig'",
        version="1.47.0",
    )

    globals()[name] = CookieBackendConfig
    return CookieBackendConfig


__all__ = ["SessionMiddleware"]
