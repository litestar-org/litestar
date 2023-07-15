from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from litestar.dto.factory._backends.abc import AbstractDTOBackend
from litestar.exceptions import MissingDependencyException
from litestar.serialization import decode_media_type

from .utils import _create_model_for_field_definitions

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.dto.factory._backends.types import FieldDefinitionsType
    from litestar.dto.interface import ConnectionContext

try:
    import pydantic
except ImportError as e:
    raise MissingDependencyException("pydantic") from e

__all__ = ("PydanticDTOBackend",)


T = TypeVar("T")


class PydanticDTOBackend(AbstractDTOBackend[pydantic.BaseModel]):
    __slots__ = ()

    def create_transfer_model_type(
        self, unique_name: str, field_definitions: FieldDefinitionsType
    ) -> type[pydantic.BaseModel]:
        fqn_uid: str = self._gen_unique_name_id(unique_name)
        model = _create_model_for_field_definitions(fqn_uid, field_definitions)
        setattr(model, "__schema_name__", unique_name)
        return model

    def parse_raw(
        self, raw: bytes, connection_context: ConnectionContext
    ) -> pydantic.BaseModel | Collection[pydantic.BaseModel]:
        return decode_media_type(  # type:ignore[no-any-return]
            raw, connection_context.request_encoding_type, type_=self.annotation
        )

    def parse_builtins(self, builtins: Any, connection_context: ConnectionContext) -> Any:
        return (
            pydantic.TypeAdapter(self.annotation).validate_python(builtins, strict=False)
            if pydantic.VERSION.startswith("2")
            else pydantic.parse_obj_as(self.annotation, builtins)
        )
