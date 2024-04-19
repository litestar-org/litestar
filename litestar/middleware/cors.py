from __future__ import annotations

from typing import Any

from litestar.middleware import _internal
from litestar.utils.deprecation import warn_deprecation


def __getattr__(name: str) -> Any:
    if name == "CORSMiddleware":
        warn_deprecation(
            version="2.9",
            deprecated_name=name,
            kind="class",
            removal_in="3.0",
            info="CORS middleware has been removed from the public API.",
        )
        return _internal.CORSMiddleware
    raise AttributeError(f"module {__name__} has no attribute {name}")
