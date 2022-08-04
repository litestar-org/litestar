from typing import Any, Dict, List, Optional, Union

from pydantic import validate_arguments
from pydantic.fields import Field, Undefined
from pydantic_openapi_schema.v3_1_0.example import Example
from pydantic_openapi_schema.v3_1_0.external_documentation import ExternalDocumentation

from starlite.enums import RequestEncodingType


@validate_arguments(config={"arbitrary_types_allowed": True})
def Parameter(
    value_type: Any = Undefined,
    *,
    header: Optional[str] = None,
    cookie: Optional[str] = None,
    query: Optional[str] = None,
    examples: Optional[List[Example]] = None,
    external_docs: Optional[ExternalDocumentation] = None,
    content_encoding: Optional[str] = None,
    required: bool = True,
    default: Any = Undefined,
    title: Optional[str] = None,
    description: Optional[str] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None
) -> Any:
    """
    Creates a pydantic FieldInfo instance with an extra kwargs,
    used for both parameter parsing and OpenAPI schema generation.
    """
    extra: Dict[str, Any] = dict(is_parameter=True)
    extra.update(header=header)
    extra.update(cookie=cookie)
    extra.update(query=query)
    extra.update(required=required)
    extra.update(examples=examples)
    extra.update(external_docs=external_docs)
    extra.update(content_encoding=content_encoding)
    extra.update(value_type=value_type)
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
    media_type: Union[str, RequestEncodingType] = RequestEncodingType.JSON,
    examples: Optional[List[Example]] = None,
    external_docs: Optional[ExternalDocumentation] = None,
    content_encoding: Optional[str] = None,
    default: Any = Undefined,
    title: Optional[str] = None,
    description: Optional[str] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    regex: Optional[str] = None
) -> Any:
    """
    Creates a pydantic FieldInfo instance with an extra kwargs,
    used for both parameter parsing and OpenAPI schema generation.
    """
    extra: Dict[str, Any] = {}
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
