# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

from litestar import Litestar, post
from litestar.params import JSONBody

if TYPE_CHECKING:
    from typing import TypeAlias

    import pydantic

    from litestar.plugins import PluginProtocol

PydanticVersion = Literal["v2"]
BaseModelType: TypeAlias = "type[pydantic.BaseModel]"


def pydantic_app(
    model: Any, *, request: bool = True, response: bool = True, plugins: Sequence[PluginProtocol] = ()
) -> Litestar:
    def with_body(data: Any) -> Any:
        return data if response else None

    def without_body() -> Any:
        return None

    handler = with_body if request else without_body
    handler.__annotations__ = {"data": JSONBody[model]} if request else {}  # type: ignore[misc]
    handler.__annotations__["return"] = model if response else None
    return Litestar([post("/", sync_to_thread=False)(handler)], plugins=[*plugins])


def pydantic_document(
    model: Any, *, request: bool = True, response: bool = True, plugins: Sequence[PluginProtocol] = ()
) -> dict[str, Any]:
    return pydantic_app(model, request=request, response=response, plugins=plugins).openapi_schema.to_schema()
