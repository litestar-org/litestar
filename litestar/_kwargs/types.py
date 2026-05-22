from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

from litestar.connection import ASGIConnection

Extractor: TypeAlias = Callable[[dict[str, Any], ASGIConnection], Awaitable[None]]
