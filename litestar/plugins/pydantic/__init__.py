from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.plugins import InitPlugin
from litestar.plugins.pydantic.dto import PydanticDTO
from litestar.plugins.pydantic.plugins.di import PydanticDIPlugin
from litestar.plugins.pydantic.plugins.init import PydanticInitPlugin
from litestar.plugins.pydantic.plugins.schema import PydanticSchemaPlugin

if TYPE_CHECKING:
    from pydantic import BaseModel
    from pydantic.v1 import BaseModel as BaseModelV1

    from litestar.config.app import AppConfig
    from litestar.types.serialization import PydanticV1FieldsListType, PydanticV2FieldsListType

__all__ = (
    "PydanticDIPlugin",
    "PydanticDTO",
    "PydanticInitPlugin",
    "PydanticPlugin",
    "PydanticSchemaPlugin",
)


def _model_dump(
    model: BaseModel | BaseModelV1,
    *,
    by_alias: bool = False,
    round_trip: bool = False,
) -> dict[str, Any]:
    return (
        model.model_dump(mode="json", by_alias=by_alias, round_trip=round_trip)  # pyright: ignore
        if hasattr(model, "model_dump")
        else {k: v.decode() if isinstance(v, bytes) else v for k, v in model.dict(by_alias=by_alias).items()}
    )


def _model_dump_json(
    model: BaseModel | BaseModelV1,
    by_alias: bool = False,
    round_trip: bool = False,
) -> str:
    return (
        model.model_dump_json(by_alias=by_alias, round_trip=round_trip)  # pyright: ignore
        if hasattr(model, "model_dump_json")
        else model.json(by_alias=by_alias)  # pyright: ignore
    )


class PydanticPlugin(InitPlugin):
    """A plugin that provides Pydantic integration."""

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
        exclude: PydanticV1FieldsListType | PydanticV2FieldsListType | None = None,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        include: PydanticV1FieldsListType | PydanticV2FieldsListType | None = None,
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

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with Pydantic.

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """
        app_config.plugins.extend(
            [
                PydanticInitPlugin(
                    exclude=self.exclude,
                    exclude_defaults=self.exclude_defaults,
                    exclude_none=self.exclude_none,
                    exclude_unset=self.exclude_unset,
                    include=self.include,
                    prefer_alias=self.prefer_alias,
                    validate_strict=self.validate_strict,
                    round_trip=self.round_trip,
                ),
                PydanticSchemaPlugin(prefer_alias=self.prefer_alias),
                PydanticDIPlugin(),
            ]
        )
        return app_config
