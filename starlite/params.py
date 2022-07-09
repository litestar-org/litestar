from __future__ import annotations

from typing import Any

from openapi_schema_pydantic.v3.v3_1_0.example import Example
from openapi_schema_pydantic.v3.v3_1_0.external_documentation import (
    ExternalDocumentation,
)
from pydantic import validate_arguments
from pydantic.fields import Field, Undefined

from starlite.enums import RequestEncodingType


@validate_arguments(config={"arbitrary_types_allowed": True})
def Parameter(
    *,
    header: str | None = None,
    cookie: str | None = None,
    query: str | None = None,
    examples: list[Example] | None = None,
    external_docs: ExternalDocumentation | None = None,
    content_encoding: str | None = None,
    required: bool = True,
    default: Any = Undefined,
    title: str | None = None,
    description: str | None = None,
    const: bool | None = None,
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    multiple_of: float | None = None,
    min_items: int | None = None,
    max_items: int | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    regex: str | None = None,
) -> Any:
    """
    Creates a pydantic FieldInfo instance with an extra kwargs,
    used for both parameter parsing and OpenAPI schema generation.
    """
    extra: dict[str, Any] = {}
    extra.update(header=header)
    extra.update(cookie=cookie)
    extra.update(query=query)
    extra.update(required=required)
    extra.update(examples=examples)
    extra.update(external_docs=external_docs)
    extra.update(content_encoding=content_encoding)
    return Field(
        default,
        alias="",
        title=title,  # type: ignore
        description=description,  # type: ignore
        const=const,  # type: ignore
        gt=gt,  # type: ignore
        ge=ge,  # type: ignore
        lt=lt,  # type: ignore
        le=le,  # type: ignore
        multiple_of=multiple_of,  # type: ignore
        min_items=min_items,  # type: ignore
        max_items=max_items,  # type: ignore
        min_length=min_length,  # type: ignore
        max_length=max_length,  # type: ignore
        regex=regex,  # type: ignore
        **extra,
    )


@validate_arguments(config={"arbitrary_types_allowed": True})
def Body(
    *,
    media_type: str | RequestEncodingType = RequestEncodingType.JSON,
    examples: list[Example] | None = None,
    external_docs: ExternalDocumentation | None = None,
    content_encoding: str | None = None,
    default: Any = Undefined,
    title: str | None = None,
    description: str | None = None,
    const: bool | None = None,
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    multiple_of: float | None = None,
    min_items: int | None = None,
    max_items: int | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    regex: str | None = None,
) -> Any:
    """
    Creates a pydantic FieldInfo instance with an extra kwargs,
    used for both parameter parsing and OpenAPI schema generation.
    """
    extra: dict[str, Any] = {}
    extra.update(media_type=media_type)
    extra.update(examples=examples)
    extra.update(external_docs=external_docs)
    extra.update(content_encoding=content_encoding)
    return Field(
        default,
        alias="",
        title=title,  # type: ignore
        description=description,  # type: ignore
        const=const,  # type: ignore
        gt=gt,  # type: ignore
        ge=ge,  # type: ignore
        lt=lt,  # type: ignore
        le=le,  # type: ignore
        multiple_of=multiple_of,  # type: ignore
        min_items=min_items,  # type: ignore
        max_items=max_items,  # type: ignore
        min_length=min_length,  # type: ignore
        max_length=max_length,  # type: ignore
        regex=regex,  # type: ignore
        **extra,
    )


@validate_arguments(config={"arbitrary_types_allowed": True})
def Dependency(*, default: Any = Undefined) -> Any:
    """
    Creates a pydantic FieldInfo instance with an extra kwargs,
    used for both parameter parsing and OpenAPI schema generation.
    """
    return Field(default, is_dependency=True)
