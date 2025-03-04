from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from typing_extensions import TypeAlias

from litestar.connection import ASGIConnection

Extractor: TypeAlias = Callable[[Dict[str, Any], ASGIConnection], Awaitable[None]]
