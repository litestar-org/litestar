from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar import Litestar


@dataclass
class Model:
    a: int
    b: str


def registered(app: Litestar, path: str = "/", method: Any = "POST") -> Any:
    """Return the handler ``app`` registered for ``path`` and ``method``, ``"websocket"`` for a websocket handler."""
    return app.route_handler_method_map[path][method]
