from __future__ import annotations

from contextlib import suppress
from functools import partial
from typing import TYPE_CHECKING, Any, TypeGuard, TypeVar, cast

import pydantic

from litestar._signature.types import ExtendedMsgSpecValidationError
from litestar.plugins import InitPlugin
from litestar.utils import is_class_and_subclass

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.config.app import AppConfig
    from litestar.plugins.pydantic.types import PydanticV2FieldsListType

T = TypeVar("T")


def _dec_pydantic_v2(model_type: type[pydantic.BaseModel], value: Any, strict: bool) -> pydantic.BaseModel:
    try:
        return model_type.model_validate(value, strict=strict)
    except pydantic.ValidationError as e:
        hide_input = model_type.model_config.get("hide_input_in_errors", False)
        raise ExtendedMsgSpecValidationError(
            errors=cast("list[dict[str, Any]]", e.errors(include_input=not hide_input))
        ) from e


_base_encoders: dict[Any, Callable[[Any], Any]] = {
    pydantic.EmailStr: str,
    pydantic.NameEmail: str,
    pydantic.ByteSize: lambda val: val.real,
}


def is_pydantic_v2_model_class(annotation: Any) -> TypeGuard[type[pydantic.BaseModel]]:  # pyright: ignore[reportInvalidTypeForm]
    return is_class_and_subclass(annotation, pydantic.BaseModel)  # pyright: ignore[reportOptionalMemberAccess]


class PydanticInitPlugin(InitPlugin):
    __slots__ = (
        "exclude",
        "exclude_defaults",
        "exclude_none",
        "exclude_unset",
        "include",
        "prefer_alias",
        "round_trip",
        "validate_strict",
    )

    def __init__(
        self,
        exclude: PydanticV2FieldsListType | None = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        include: PydanticV2FieldsListType | None = None,
        prefer_alias: bool = False,
        validate_strict: bool = False,
        round_trip: bool = False,
    ) -> None:
        """Pydantic Plugin to support serialization / validation of Pydantic types / models

        :param exclude: Fields to exclude during serialization
        :param exclude_defaults: Fields to exclude during serialization when they are set to their default value
        :param exclude_none: Fields to exclude during serialization when they are set to ``None``
        :param exclude_unset: Fields to exclude during serialization when they arenot set
        :param include: Fields to exclude during serialization
        :param prefer_alias: Use the ``by_alias=True`` flag when dumping models
        :param validate_strict: Use ``strict=True`` when calling ``.model_validate`` on Pydantic 2.x models
        :param round_trip: use ``round_trip=True`` when calling ``.model_dump``
          and ``.model_dump_json`` on Pydantic 2.x models
        """
        self.exclude = exclude
        self.exclude_defaults = exclude_defaults
        self.exclude_none = exclude_none
        self.exclude_unset = exclude_unset
        self.include = include
        self.prefer_alias = prefer_alias
        self.validate_strict = validate_strict
        self.round_trip = round_trip

    @classmethod
    def encoders(
        cls,
        exclude: PydanticV2FieldsListType | None = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        include: PydanticV2FieldsListType | None = None,
        prefer_alias: bool = False,
        round_trip: bool = False,
    ) -> dict[Any, Callable[[Any], Any]]:
        return {
            **_base_encoders,
            **cls._create_pydantic_v2_encoders(
                prefer_alias=prefer_alias,
                exclude=exclude,  # type: ignore[arg-type]
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                exclude_unset=exclude_unset,
                include=include,  # type: ignore[arg-type]
                round_trip=round_trip,
            ),
        }

    @classmethod
    def decoders(cls, validate_strict: bool = False) -> list[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]]:
        return [(is_pydantic_v2_model_class, partial(_dec_pydantic_v2, strict=validate_strict))]

    @staticmethod
    def _create_pydantic_v2_encoders(
        exclude: PydanticV2FieldsListType | None = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        include: PydanticV2FieldsListType | None = None,
        prefer_alias: bool = False,
        round_trip: bool = False,
    ) -> dict[Any, Callable[[Any], Any]]:
        encoders: dict[Any, Callable[[Any], Any]] = {
            pydantic.BaseModel: lambda model: model.model_dump(  # pyright: ignore[reportOptionalMemberAccess]
                by_alias=prefer_alias,
                exclude=exclude,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                exclude_unset=exclude_unset,
                include=include,
                mode="json",
                round_trip=round_trip,
            ),
            pydantic.types.SecretStr: lambda val: "**********" if val else "",  # pyright: ignore[reportOptionalMemberAccess]
            pydantic.types.SecretBytes: lambda val: "**********" if val else "",  # pyright: ignore[reportOptionalMemberAccess]
            pydantic.AnyUrl: str,  # pyright: ignore[reportOptionalMemberAccess]
        }

        with suppress(ImportError):
            from pydantic_extra_types import color

            encoders[color.Color] = str

        return encoders

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.type_encoders = {
            **self.encoders(
                prefer_alias=self.prefer_alias,
                exclude=self.exclude,
                exclude_defaults=self.exclude_defaults,
                exclude_none=self.exclude_none,
                exclude_unset=self.exclude_unset,
                include=self.include,
                round_trip=self.round_trip,
            ),
            **(app_config.type_encoders or {}),
        }
        app_config.type_decoders = [
            *self.decoders(validate_strict=self.validate_strict),
            *(app_config.type_decoders or []),
        ]

        return app_config
