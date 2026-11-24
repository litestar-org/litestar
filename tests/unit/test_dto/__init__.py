from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar.dto._plan import create_backend, resolve_dto_target

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.dto import AbstractDTO
    from litestar.dto._backend import DTOBackend
    from litestar.typing import FieldDefinition


@dataclass
class Model:
    a: int
    b: str


def registered(app: Litestar, path: str = "/", method: Any = "POST") -> Any:
    """Return the handler ``app`` registered for ``path`` and ``method``, ``"websocket"`` for a websocket handler."""
    return app.route_handler_method_map[path][method]


def create_backend_for(
    dto: type[AbstractDTO[Any]], field_definition: FieldDefinition, *, is_data_field: bool, **kwargs: Any
) -> DTOBackend:
    target = resolve_dto_target(dto, field_definition, is_data_field=is_data_field)
    assert target is not None
    return create_backend(dto, target, is_data_field=is_data_field, **kwargs)
