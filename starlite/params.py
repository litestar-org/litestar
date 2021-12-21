from typing import Any, Optional

from openapi_schema_pydantic import ExternalDocumentation
from pydantic.fields import Field, Undefined
from pydantic.typing import NoArgAnyCallable


def Parameter(  # pylint: disable=too-many-locals
    *,
    header: Optional[str] = None,
    cookie: Optional[str] = None,
    query: Optional[str] = None,
    example: Any = None,
    examples: Optional[list] = None,
    external_docs: Optional[ExternalDocumentation] = None,
    content_encoding: Optional[str] = None,
    required: bool = True,
    default: Any = Undefined,
    default_factory: Optional[NoArgAnyCallable] = None,
    alias: str = None,
    title: str = None,
    description: str = None,
    const: bool = None,
    gt: float = None,
    ge: float = None,
    lt: float = None,
    le: float = None,
    multiple_of: float = None,
    min_items: int = None,
    max_items: int = None,
    min_length: int = None,
    max_length: int = None,
    regex: str = None,
    **extra: Any,
) -> Any:
    """
    Creates a pydantic FieldInfo instance with an extra kwargs,
    used for both parameter parsing and OpenAPI schema generation.
    """
    extra.update(header=header)
    extra.update(cookie=cookie)
    extra.update(query=query)
    extra.update(required=required)
    extra.update(example=example)
    extra.update(examples=examples)
    extra.update(external_docs=external_docs)
    extra.update(content_encoding=content_encoding)
    return Field(
        default,
        default_factory=default_factory,
        alias=alias,
        title=title,
        description=description,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        min_items=min_items,
        max_items=max_items,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        **extra,
    )
