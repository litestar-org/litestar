from __future__ import annotations

import warnings
from functools import cache
from typing import TYPE_CHECKING, Any

import pydantic
from pydantic import networks

from litestar._openapi.schema_generation.library.converter import json_schema_to_spec
from litestar.exceptions import ImproperlyConfiguredException, LitestarWarning
from litestar.plugins import OpenAPISchemaPlugin
from litestar.plugins.pydantic.utils import is_pydantic_model_class, is_pydantic_undefined
from litestar.utils import is_class_and_subclass

if TYPE_CHECKING:
    from litestar._openapi.schema_generation.library import SchemaMode
    from litestar._openapi.schema_generation.schema import SchemaCreator
    from litestar.openapi.spec import Reference, Schema
    from litestar.typing import FieldDefinition

_supported_types: tuple[Any, ...] = (
    pydantic.BaseModel,
    pydantic.SecretStr,
    pydantic.SecretBytes,
    pydantic.ByteSize,
    pydantic.EmailStr,
    pydantic.IPvAnyAddress,
    pydantic.IPvAnyInterface,
    pydantic.IPvAnyNetwork,
    pydantic.Json,
    pydantic.NameEmail,
    pydantic.AnyUrl,
    pydantic.PastDate,
    pydantic.FutureDate,
    pydantic.PastDatetime,
    pydantic.FutureDatetime,
    pydantic.AwareDatetime,
    pydantic.NaiveDatetime,
    *(url for url in (networks.HttpUrl, networks.AnyHttpUrl) if isinstance(url, type)),
)

_MINIMUM_PYDANTIC_VERSION = (2, 11)


class PydanticSchemaPlugin(OpenAPISchemaPlugin):
    def __init__(self, prefer_alias: bool = False) -> None:
        if prefer_alias:
            warnings.warn(
                "PydanticSchemaPlugin(prefer_alias=True) has no effect: response schemas follow the prefer_alias "
                "option of PydanticPlugin or PydanticInitPlugin, which serialize the models",
                category=LitestarWarning,
                stacklevel=2,
            )
        self.prefer_alias = prefer_alias

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "for_pydantic_model" in cls.__dict__:
            warnings.warn(
                f"{cls.__qualname__}.for_pydantic_model is never called: PydanticSchemaPlugin no longer has this "
                "hook. Override to_openapi_schema and return your own schema instead",
                category=LitestarWarning,
                stacklevel=3,
            )

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        return isinstance(value, _supported_types) or is_class_and_subclass(value, _supported_types)  # type: ignore[arg-type]

    @staticmethod
    def is_undefined_sentinel(value: Any) -> bool:
        return is_pydantic_undefined(value)

    def to_openapi_schema(self, field_definition: FieldDefinition, schema_creator: SchemaCreator) -> Schema | Reference:
        """Given a type annotation, transform it into an OpenAPI schema class.

        Pydantic models and types are documented with pydantic's own JSON schema generation.

        Args:
            field_definition: FieldDefinition instance.
            schema_creator: An instance of the schema creator class

        Returns:
            An :class:`OpenAPI <litestar.openapi.spec.schema.Schema>` instance.
        """
        from litestar.plugins.pydantic.plugins._json_schema import PYDANTIC_RESOLVER

        if is_pydantic_model_class(field_definition.annotation):
            _check_pydantic_version()
            return schema_creator.for_library(field_definition, PYDANTIC_RESOLVER)
        return _type_schema(field_definition.annotation, schema_creator.schema_mode)


def _check_pydantic_version() -> None:
    if not _is_supported_pydantic_version(pydantic.VERSION):
        raise ImproperlyConfiguredException(
            f"Documenting pydantic models requires pydantic 2.11 or later, but pydantic {pydantic.VERSION} is installed"
        )


@cache
def _is_supported_pydantic_version(version: str) -> bool:
    major, minor, *_ = version.split(".")
    return (int(major), int(minor)) >= _MINIMUM_PYDANTIC_VERSION


def _type_schema(annotation: Any, mode: SchemaMode) -> Schema | Reference:
    def lookup_ref(ref: str) -> Schema | Reference:
        raise ImproperlyConfiguredException(f"Cannot resolve {ref!r} in the pydantic schema of {annotation!r}")

    return json_schema_to_spec(_json_schema(annotation, mode), lookup_ref)


@cache
def _json_schema(annotation: Any, mode: SchemaMode) -> dict[str, Any]:
    try:
        return pydantic.TypeAdapter(annotation).json_schema(mode=mode)
    except pydantic.PydanticInvalidForJsonSchema:
        return {}
