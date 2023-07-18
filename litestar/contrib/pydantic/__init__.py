from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .pydantic_dto_factory import PydanticDTO
from .pydantic_init_plugin import PydanticInitPlugin
from .pydantic_schema_plugin import PydanticSchemaPlugin

if TYPE_CHECKING:
    import pydantic

__all__ = ("PydanticDTO", "PydanticInitPlugin", "PydanticSchemaPlugin")


def _model_dump(model: pydantic.BaseModel, *, by_alias: bool = False) -> dict[str, Any]:
    return (
        model.model_dump(mode="json", by_alias=by_alias)
        if hasattr(model, "model_dump")
        else model.dict(by_alias=by_alias)
    )


def _model_dump_json(model: pydantic.BaseModel) -> str:
    return model.model_dump_json() if hasattr(model, "model_dump_json") else model.json()
