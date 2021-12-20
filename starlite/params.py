from typing import Any, Optional

from pydantic.fields import Field, Undefined
from pydantic.typing import NoArgAnyCallable


def Header(
    header_key: str,
    *,
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
    allow_mutation: bool = True,
    regex: str = None,
    **extra: Any,
) -> Any:
    """
    Creates a pydantic FieldInfo instance with the header_key and required kwargs as part of the extra dict
    """
    extra.update(starlite_header_key=header_key)
    extra.update(starlite_required=required)
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
        allow_mutation=allow_mutation,
        regex=regex,
        **extra,
    )
