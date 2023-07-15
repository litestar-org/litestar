from __future__ import annotations

from typing import Any, Callable, TypeVar, cast
from uuid import UUID

from msgspec import ValidationError

from litestar.serialization._msgspec_utils import ExtendedMsgSpecValidationError
from litestar.utils import is_class_and_subclass, is_pydantic_model_class

__all__ = (
    "create_pydantic_decoders",
    "create_pydantic_encoders",
)

T = TypeVar("T")


def create_pydantic_decoders() -> list[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]]:
    decoders: list[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]] = []
    try:
        import pydantic

        def _dec_pydantic(type_: type[pydantic.BaseModel], value: Any) -> pydantic.BaseModel:
            try:
                return (
                    type_.model_validate(value, strict=False)
                    if hasattr(type_, "model_validate")
                    else type_.parse_obj(value)
                )
            except pydantic.ValidationError as e:
                raise ExtendedMsgSpecValidationError(errors=cast("list[dict[str, Any]]", e.errors())) from e

        decoders.append((is_pydantic_model_class, _dec_pydantic))

        def _dec_pydantic_uuid(
            type_: type[pydantic.UUID1] | type[pydantic.UUID3] | type[pydantic.UUID4] | type[pydantic.UUID5], val: Any
        ) -> type[pydantic.UUID1] | type[pydantic.UUID3] | type[pydantic.UUID4] | type[pydantic.UUID5]:
            if isinstance(val, str):
                val = type_(val)

            elif isinstance(val, (bytes, bytearray)):
                try:
                    val = type_(val.decode())
                except ValueError:
                    # 16 bytes in big-endian order as the bytes argument fail
                    # the above check
                    val = type_(bytes=val)
            elif isinstance(val, UUID):
                val = type_(str(val))

            if not isinstance(val, type_):
                raise ValidationError(f"Invalid UUID: {val!r}")

            if type_._required_version != val.version:  # type: ignore
                raise ValidationError(f"Invalid UUID version: {val!r}")

            return cast(
                "type[pydantic.UUID1] | type[pydantic.UUID3] | type[pydantic.UUID4] | type[pydantic.UUID5]", val
            )

        def _is_pydantic_uuid(value: Any) -> bool:
            return is_class_and_subclass(value, (pydantic.UUID1, pydantic.UUID3, pydantic.UUID4, pydantic.UUID5))

        decoders.append((_is_pydantic_uuid, _dec_pydantic_uuid))
        return decoders
    except ImportError:
        return decoders


def create_pydantic_encoders() -> dict[Any, Callable[[Any], Any]]:
    try:
        import pydantic

        encoders: dict[Any, Callable[[Any], Any]] = {
            pydantic.EmailStr: str,
            pydantic.NameEmail: str,
            pydantic.ByteSize: lambda val: val.real,
        }

        if pydantic.VERSION.startswith("1"):  # pragma: no cover
            encoders.update(
                {
                    pydantic.BaseModel: lambda model: model.dict(),
                    pydantic.SecretField: str,
                    pydantic.StrictBool: int,
                    pydantic.color.Color: str,  # pyright: ignore
                    pydantic.ConstrainedBytes: lambda val: val.decode("utf-8"),
                    pydantic.ConstrainedDate: lambda val: val.isoformat(),
                }
            )
        else:
            from pydantic_extra_types import color

            encoders.update(
                {
                    pydantic.BaseModel: lambda model: model.model_dump(mode="json"),
                    color.Color: str,
                    pydantic.types.SecretStr: lambda val: "**********" if val else "",
                    pydantic.types.SecretBytes: lambda val: "**********" if val else "",
                }
            )
        return encoders
    except ImportError:
        return {}
