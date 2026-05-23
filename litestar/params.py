from __future__ import annotations

import warnings
from collections.abc import Hashable, Sequence
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, TypeAlias, TypeVar

from litestar.enums import ParamType, RequestEncodingType
from litestar.types import Empty

__all__ = (
    "Body",
    "BodyKwarg",
    "CookieParameter",
    "FromCookie",
    "FromHeader",
    "FromPath",
    "FromQuery",
    "HeaderParameter",
    "JSONBody",
    "KwargDefinition",
    "MsgPackBody",
    "MultipartBody",
    "ParameterKwarg",
    "PathParameter",
    "QueryParameter",
    "SkipValidation",
    "SkipValidationMarker",
    "URLEncodedBody",
)

if TYPE_CHECKING:
    from litestar.openapi.spec.example import Example
    from litestar.openapi.spec.external_documentation import (
        ExternalDocumentation,
    )


T = TypeVar("T")


@dataclass(frozen=True)
class KwargDefinition:
    """Data container representing a constrained kwarg."""

    examples: list[Example] | None = field(default=None)
    """A list of Example models."""
    external_docs: ExternalDocumentation | None = field(default=None)
    """A url pointing at external documentation for the given parameter."""
    content_encoding: str | None = field(default=None)
    """The content encoding of the value.

    Applicable on to string values. See OpenAPI 3.1 for details.
    """
    title: str | None = field(default=None)
    """String value used in the title section of the OpenAPI schema for the given parameter."""
    description: str | None = field(default=None)
    """String value used in the description section of the OpenAPI schema for the given parameter."""
    const: bool | None = field(default=None)
    """A boolean flag dictating whether this parameter is a constant.

    If True, the value passed to the parameter must equal its default value. This also causes the OpenAPI const field to
    be populated with the default value.
    """
    gt: float | None = field(default=None)
    """Constrict value to be greater than a given float or int.

    Equivalent to exclusiveMinimum in the OpenAPI specification.
    """
    ge: float | None = field(default=None)
    """Constrict value to be greater or equal to a given float or int.

    Equivalent to minimum in the OpenAPI specification.
    """
    lt: float | None = field(default=None)
    """Constrict value to be less than a given float or int.

    Equivalent to exclusiveMaximum in the OpenAPI specification.
    """
    le: float | None = field(default=None)
    """Constrict value to be less or equal to a given float or int.

    Equivalent to maximum in the OpenAPI specification.
    """
    multiple_of: float | None = field(default=None)
    """Constrict value to a multiple of a given float or int.

    Equivalent to multipleOf in the OpenAPI specification.
    """
    min_items: int | None = field(default=None)
    """Constrict a set or a list to have a minimum number of items.

    Equivalent to minItems in the OpenAPI specification.
    """
    max_items: int | None = field(default=None)
    """Constrict a set or a list to have a maximum number of items.

    Equivalent to maxItems in the OpenAPI specification.
    """
    min_length: int | None = field(default=None)
    """Constrict a string or bytes value to have a minimum length.

    Equivalent to minLength in the OpenAPI specification.
    """
    max_length: int | None = field(default=None)
    """Constrict a string or bytes value to have a maximum length.

    Equivalent to maxLength in the OpenAPI specification.
    """
    pattern: str | None = field(default=None)
    """A string representing a regex against which the given string will be matched.

    Equivalent to pattern in the OpenAPI specification.
    """
    lower_case: bool | None = field(default=None)
    """Constrict a string value to be lower case."""
    upper_case: bool | None = field(default=None)
    """Constrict a string value to be upper case."""
    format: str | None = field(default=None)
    """Specify the format to which a string value should be converted."""
    enum: Sequence[Any] | None = field(default=None)
    """A sequence of valid values."""
    read_only: bool | None = field(default=None)
    """A boolean flag dictating whether this parameter is read only."""
    schema_extra: dict[str, Any] | None = field(default=None)
    """Extensions to the generated schema.

    If set, will overwrite the matching fields in the generated schema.

    .. versionadded:: 2.8.0
    """
    schema_component_key: str | None = None
    """
    Use as the key for the reference when creating a component for this type
    .. versionadded:: 2.12.0
    """
    include_in_schema: bool = True
    """
    A boolean flag dictating whether this parameter should be included in the schema.
    .. versionadded:: 2.17.0
    """

    @property
    def is_constrained(self) -> bool:
        """Return True if any of the constraints are set."""
        return any(
            attr is not None
            for attr in (
                self.gt,
                self.ge,
                self.lt,
                self.le,
                self.multiple_of,
                self.min_items,
                self.max_items,
                self.min_length,
                self.max_length,
                self.pattern,
                self.const,
                self.lower_case,
                self.upper_case,
            )
        )


@dataclass(frozen=True)
class ParameterKwarg(KwargDefinition):
    """Data container representing a parameter."""

    param_type: ClassVar[ParamType] = ParamType.QUERY
    """Type of the parameter"""

    name: str | None = None
    """
    Name of the parameter. If 'None', and used in a function annotation, the name
    will be inferred from the annotated parameter's name.
    """
    annotation: Any = field(default=Empty)
    """The field value - `Empty` by default."""
    header: str | None = field(default=None)
    """The header name - required for header parameters."""
    cookie: str | None = field(default=None)
    """The cookie name - required for cookie parameters."""
    query: str | None = field(default=None)
    """The query parameter name - required for query parameters"""
    required: bool | None = field(default=None)
    """A boolean flag dictating whether this parameter is required.

    If set to False, None values will be allowed. Defaults to True.
    """

    @property
    def is_marker(self) -> bool:
        return not self.is_constrained and not self.name and self.required is None

    def __hash__(self) -> int:  # pragma: no cover
        """Hash the dataclass in a safe way.

        Returns:
            A hash
        """
        return sum(hash(v) for v in asdict(self) if isinstance(v, Hashable))

    def __post_init__(self) -> None:
        if (header := self.header) is not None:
            warnings.warn(
                f"Deprecated 'header' parameter: Parameter(header={header!r}). Use 'HeaderParameter(name={header!r})' instead",
                stacklevel=2,
                category=DeprecationWarning,
            )
            object.__setattr__(self, "name", header)
            object.__setattr__(self, "param_type", ParamType.HEADER)
        if (cookie := self.cookie) is not None:
            warnings.warn(
                f"Deprecated 'cookie' parameter: Parameter(cookie={cookie!r}). Use 'CookieParameter(name={cookie!r})' instead",
                stacklevel=2,
                category=DeprecationWarning,
            )
            object.__setattr__(self, "name", cookie)
            object.__setattr__(self, "param_type", ParamType.COOKIE)
        if (query := self.query) is not None:
            warnings.warn(
                f"Deprecated 'query' parameter: Parameter(query={query!r}). Use 'QueryParameter(name={query!r})' instead",
                stacklevel=2,
                category=DeprecationWarning,
            )
            object.__setattr__(self, "name", query)
            object.__setattr__(self, "param_type", ParamType.QUERY)


class QueryParameter(ParameterKwarg):
    """Describes a query parameter.

    In the OpenAPI, this maps to a parameter ``in: query``.
    """

    param_type = ParamType.QUERY


class HeaderParameter(ParameterKwarg):
    """Describes a header parameter.

    In the OpenAPI, this maps to a parameter ``in: header``.
    """

    param_type = ParamType.HEADER


class CookieParameter(ParameterKwarg):
    """Describes a cookie parameter.

    In the OpenAPI, this maps to a parameter ``in: cookie``.
    """

    param_type = ParamType.COOKIE


class PathParameter(ParameterKwarg):
    """Describes a path parameter.

    In the OpenAPI, this maps to a parameter ``in: path``.
    """

    param_type = ParamType.PATH


FromQuery: TypeAlias = Annotated[T, QueryParameter()]
"""Declare a query parameter"""

FromHeader: TypeAlias = Annotated[T, HeaderParameter()]
"""Declare a header parameter"""

FromCookie: TypeAlias = Annotated[T, CookieParameter()]
"""Declare a cookie parameter"""

FromPath: TypeAlias = Annotated[T, PathParameter()]
"""Declare a path parameter"""


@dataclass(frozen=True)
class BodyKwarg(KwargDefinition):
    """Data container representing a request body."""

    media_type: str | RequestEncodingType = field(default=RequestEncodingType.JSON)
    """Media-Type of the body."""

    multipart_form_part_limit: int | None = field(default=None)
    """The maximal number of allowed parts in a multipart/formdata request. This limit is intended to protect from DoS attacks."""

    def __hash__(self) -> int:  # pragma: no cover
        """Hash the dataclass in a safe way.

        Returns:
            A hash
        """
        return sum(hash(v) for v in asdict(self) if isinstance(v, Hashable))


JSONBody: TypeAlias = Annotated[T, BodyKwarg(media_type=RequestEncodingType.JSON)]
"""Declare a 'application/json request body"""

MsgPackBody: TypeAlias = Annotated[T, BodyKwarg(media_type=RequestEncodingType.MESSAGEPACK)]
"""Declare a 'application/x-msgpack' request body"""

MultipartBody: TypeAlias = Annotated[T, BodyKwarg(media_type=RequestEncodingType.MULTI_PART)]
"""Declare a 'multipart/form-data' request body"""

URLEncodedBody: TypeAlias = Annotated[T, BodyKwarg(media_type=RequestEncodingType.URL_ENCODED)]
"""Declare a 'application/x-www-form-urlencoded' request body"""


def Body(
    *,
    const: bool | None = None,
    content_encoding: str | None = None,
    description: str | None = None,
    examples: list[Example] | None = None,
    external_docs: ExternalDocumentation | None = None,
    ge: float | None = None,
    gt: float | None = None,
    le: float | None = None,
    lt: float | None = None,
    max_items: int | None = None,
    max_length: int | None = None,
    media_type: str | RequestEncodingType = RequestEncodingType.JSON,
    min_items: int | None = None,
    min_length: int | None = None,
    multipart_form_part_limit: int | None = None,
    multiple_of: float | None = None,
    pattern: str | None = None,
    title: str | None = None,
    schema_extra: dict[str, Any] | None = None,
    schema_component_key: str | None = None,
) -> Any:
    """Create an extended request body kwarg definition.

    Args:
        const: A boolean flag dictating whether this parameter is a constant. If True, the value passed to the parameter
            must equal its default value. This also causes the OpenAPI const field to be
            populated with the default value.
        content_encoding: The content encoding of the value. Applicable on to string values.
            See OpenAPI 3.1 for details.
        description: String value used in the description section of the OpenAPI schema for the given parameter.
        examples: A list of Example models.
        external_docs: A url pointing at external documentation for the given parameter.
        ge: Constrict value to be greater or equal to a given float or int.
            Equivalent to minimum in the OpenAPI specification.
        gt: Constrict value to be greater than a given float or int.
            Equivalent to exclusiveMinimum in the OpenAPI specification.
        le: Constrict value to be less or equal to a given float or int.
            Equivalent to maximum in the OpenAPI specification.
        lt: Constrict value to be less than a given float or int.
            Equivalent to exclusiveMaximum in the OpenAPI specification.
        max_items: Constrict a set or a list to have a maximum number of items.
            Equivalent to maxItems in the OpenAPI specification.
        max_length: Constrict a string or bytes value to have a maximum length.
            Equivalent to maxLength in the OpenAPI specification.
        media_type: Defaults to RequestEncodingType.JSON.
        min_items: Constrict a set or a list to have a minimum number of items.
            Equivalent to minItems in the OpenAPI specification.
        min_length: Constrict a string or bytes value to have a minimum length.
            Equivalent to minLength in the OpenAPI specification.
        multipart_form_part_limit: The maximal number of allowed parts in a multipart/formdata request.
            This limit is intended to protect from DoS attacks.
        multiple_of: Constrict value to a multiple of a given float or int.
            Equivalent to multipleOf in the OpenAPI specification.
        pattern: A string representing a regex against which the given string will be matched.
            Equivalent to pattern in the OpenAPI specification.
        title: String value used in the title section of the OpenAPI schema for the given parameter.
        schema_extra: Extensions to the generated schema. If set, will overwrite the matching fields in the generated
            schema.

            .. versionadded:: 2.8.0
        schema_component_key: Use this as the key for the reference when creating a component for this type
            .. versionadded:: 2.12.0
    """
    return BodyKwarg(
        media_type=media_type,
        examples=examples,
        external_docs=external_docs,
        content_encoding=content_encoding,
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
        pattern=pattern,
        multipart_form_part_limit=multipart_form_part_limit,
        schema_extra=schema_extra,
        schema_component_key=schema_component_key,
    )


class SkipValidationMarker:
    """Indicate that a type annotated with this as metadata should be
    treated as 'Any'
    """


SkipValidation: TypeAlias = Annotated[T, SkipValidationMarker()]
"""Exclude 'T' from validation, effectively treating it as 'Any'"""
