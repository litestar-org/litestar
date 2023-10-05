from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast
from uuid import UUID

from msgspec import ValidationError

from litestar._signature.types import ExtendedMsgSpecValidationError
from litestar.exceptions import MissingDependencyException
from litestar.plugins import InitPluginProtocol
from litestar.utils import is_class_and_subclass, is_pydantic_model_class

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

try:
    import pydantic
except ImportError as e:
    raise MissingDependencyException("pydantic") from e

T = TypeVar("T")


def _dec_pydantic(model_type: type[pydantic.BaseModel], value: Any) -> pydantic.BaseModel:
    try:
        return (
            model_type.model_validate(value, strict=False)
            if hasattr(model_type, "model_validate")
            else model_type.parse_obj(value)
        )
    except pydantic.ValidationError as e:
        raise ExtendedMsgSpecValidationError(errors=cast("list[dict[str, Any]]", e.errors())) from e


def _dec_pydantic_uuid(
    uuid_type: type[pydantic.UUID1] | type[pydantic.UUID3] | type[pydantic.UUID4] | type[pydantic.UUID5],
    value: Any,
) -> type[pydantic.UUID1] | type[pydantic.UUID3] | type[pydantic.UUID4] | type[pydantic.UUID5]:  # pragma: no cover
    if isinstance(value, str):
        value = uuid_type(value)

    elif isinstance(value, (bytes, bytearray)):
        try:
            value = uuid_type(value.decode())
        except ValueError:
            # 16 bytes in big-endian order as the bytes argument fail
            # the above check
            value = uuid_type(bytes=value)
    elif isinstance(value, UUID):
        value = uuid_type(str(value))

    if not isinstance(value, uuid_type):
        raise ValidationError(f"Invalid UUID: {value!r}")

    if value._required_version != value.version:  # pyright: ignore
        raise ValidationError(f"Invalid UUID version: {value!r}")

    return cast("type[pydantic.UUID1] | type[pydantic.UUID3] | type[pydantic.UUID4] | type[pydantic.UUID5]", value)


def _is_pydantic_uuid(value: Any) -> bool:  # pragma: no cover
    return is_class_and_subclass(value, (pydantic.UUID1, pydantic.UUID3, pydantic.UUID4, pydantic.UUID5))


_base_encoders: dict[Any, Callable[[Any], Any]] = {
    pydantic.EmailStr: str,
    pydantic.NameEmail: str,
    pydantic.ByteSize: lambda val: val.real,
}


class PydanticInitPlugin(InitPluginProtocol):
    __slots__ = ("prefer_alias",)

    def __init__(self, prefer_alias: bool = False) -> None:
        self.prefer_alias = prefer_alias

    @classmethod
    def encoders(cls, prefer_alias: bool = False) -> dict[Any, Callable[[Any], Any]]:
        if pydantic.VERSION.startswith("1"):  # pragma: no cover
            return {**_base_encoders, **cls._create_pydantic_v1_encoders(prefer_alias)}
        return {**_base_encoders, **cls._create_pydantic_v2_encoders(prefer_alias)}

    @classmethod
    def decoders(cls) -> list[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]]:
        decoders: list[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]] = [
            (is_pydantic_model_class, _dec_pydantic)
        ]

        if pydantic.VERSION.startswith("1"):  # pragma: no cover
            decoders.append((_is_pydantic_uuid, _dec_pydantic_uuid))

        return decoders

    @staticmethod
    def _create_pydantic_v1_encoders(prefer_alias: bool = False) -> dict[Any, Callable[[Any], Any]]:  # pragma: no cover
        return {
            pydantic.BaseModel: lambda model: {
                k: v.decode() if isinstance(v, bytes) else v for k, v in model.dict(by_alias=prefer_alias).items()
            },
            pydantic.SecretField: str,
            pydantic.StrictBool: int,
            pydantic.color.Color: str,  # pyright: ignore
            pydantic.ConstrainedBytes: lambda val: val.decode("utf-8"),
            pydantic.ConstrainedDate: lambda val: val.isoformat(),
        }

    @staticmethod
    def _create_pydantic_v2_encoders(prefer_alias: bool = False) -> dict[Any, Callable[[Any], Any]]:
        encoders: dict[Any, Callable[[Any], Any]] = {
            pydantic.BaseModel: lambda model: model.model_dump(mode="json", by_alias=prefer_alias),
            pydantic.types.SecretStr: lambda val: "**********" if val else "",
            pydantic.types.SecretBytes: lambda val: "**********" if val else "",
        }

        with suppress(ImportError):
            from pydantic_extra_types import color

            encoders[color.Color] = str

        return encoders

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.type_encoders = {**self.encoders(self.prefer_alias), **(app_config.type_encoders or {})}
        app_config.type_decoders = [*self.decoders(), *(app_config.type_decoders or [])]
        return app_config
