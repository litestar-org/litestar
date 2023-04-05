from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Hashable

from litestar.enums import RequestEncodingType
from litestar.types import Empty

__all__ = ("Body", "BodyKwarg", "Dependency", "DependencyKwarg", "Parameter", "ParameterKwarg")


if TYPE_CHECKING:
    from litestar.openapi.spec.example import Example
    from litestar.openapi.spec.external_documentation import (
        ExternalDocumentation,
    )


@dataclass(frozen=True)
class ParameterKwarg:
    """Data container representing a parameter."""

    value_type: Any = field(default=Empty)
    """The field value - `Empty` by default."""
    header: str | None = field(default=None)
    """The header parameter key - required for header parameters."""
    cookie: str | None = field(default=None)
    """The cookie parameter key - required for cookie parameters."""
    query: str | None = field(default=None)
    """The query parameter key for this parameter."""
    examples: list[Example] | None = field(default=None)
    """A list of Example models."""
    external_docs: ExternalDocumentation | None = field(default=None)
    """A url pointing at external documentation for the given parameter."""
    content_encoding: str | None = field(default=None)
    """The content encoding of the value.

    Applicable on to string values. See OpenAPI 3.1 for details.
    """
    required: bool | None = field(default=None)
    """A boolean flag dictating whether this parameter is required.

    If set to False, None values will be allowed. Defaults to True.
    """
    default: Any = field(default=Empty)
    """A default value.

    If const is true, this value is required.
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
    regex: str | None = field(default=None)
    """A string representing a regex against which the given string will be matched.

    Equivalent to pattern in the OpenAPI specification.
    """

    def __hash__(self) -> int:  # pragma: no cover
        """Hash the dataclass in a safe way.

        Returns:
            A hash
        """
        return sum(hash(v) for v in asdict(self) if isinstance(v, Hashable))


def Parameter(
    value_type: Any = Empty,
    *,
    header: str | None = None,
    cookie: str | None = None,
    query: str | None = None,
    examples: list[Example] | None = None,
    external_docs: ExternalDocumentation | None = None,
    content_encoding: str | None = None,
    required: bool | None = None,
    default: Any = Empty,
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
    """Create an extended parameter kwarg definition.

    Args:
        value_type: `Empty` by default.
        header: The header parameter key - required for header parameters.
        cookie: The cookie parameter key - required for cookie parameters.
        query: The query parameter key for this parameter.
        examples: A list of Example models.
        external_docs: A url pointing at external documentation for the given
            parameter.
        content_encoding: The content encoding of the value. Applicable on to string values. See
            OpenAPI 3.1 for details.
        required: A boolean flag dictating whether this parameter is required. If set to False, None
            values will be allowed. Defaults to True.
        default: A default value. If const is true, this value is required.
        title: String value used in the title section of the OpenAPI schema for the given
            parameter.
        description: String value used in the description section of the OpenAPI schema for the
            given parameter.
        const: A boolean flag dictating whether this parameter is a constant. If True, the value passed
            to the parameter must equal its default value. This also causes the OpenAPI const field to be populated with
            the default value.
        gt: Constrict value to be greater than a given float or int. Equivalent to
            exclusiveMinimum in the OpenAPI specification.
        ge: Constrict value to be greater or equal to a given float or int. Equivalent to
            minimum in the OpenAPI specification.
        lt: Constrict value to be less than a given float or int. Equivalent to
            exclusiveMaximum in the OpenAPI specification.
        le: Constrict value to be less or equal to a given float or int. Equivalent to maximum
            in the OpenAPI specification.
        multiple_of: Constrict value to a multiple of a given float or int. Equivalent to
            multipleOf in the OpenAPI specification.
        min_items: Constrict a set or a list to have a minimum number of items. Equivalent to
            minItems in the OpenAPI specification.
        max_items: Constrict a set or a list to have a maximum number of items. Equivalent to
            maxItems in the OpenAPI specification.
        min_length: Constrict a string or bytes value to have a minimum length. Equivalent to
            minLength in the OpenAPI specification.
        max_length: Constrict a string or bytes value to have a maximum length. Equivalent to
            maxLength in the OpenAPI specification.
        regex: A string representing a regex against which the given string will be matched.
            Equivalent to pattern in the OpenAPI specification.
    """
    return ParameterKwarg(
        value_type=value_type,
        header=header,
        cookie=cookie,
        query=query,
        examples=examples,
        external_docs=external_docs,
        content_encoding=content_encoding,
        required=required,
        default=default,
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
    )


@dataclass(frozen=True)
class BodyKwarg:
    """Data container representing a request body."""

    media_type: str | RequestEncodingType = field(default=RequestEncodingType.JSON)
    """Media-Type of the body."""
    examples: list[Example] | None = field(default=None)
    """A list of Example models."""
    external_docs: ExternalDocumentation | None = field(default=None)
    """A url pointing at external documentation for the given parameter."""
    content_encoding: str | None = field(default=None)
    """The content encoding of the value.

    Applicable on to string values. See OpenAPI 3.1 for details.
    """
    default: Any = field(default=Empty)
    """A default value.

    If const is true, this value is required.
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
    regex: str | None = field(default=None)
    """A string representing a regex against which the given string will be matched.

    Equivalent to pattern in the OpenAPI specification.
    """
    multipart_form_part_limit: int | None = field(default=None)
    """The maximal number of allowed parts in a multipart/formdata request. This limit is intended to protect from DoS attacks."""

    def __hash__(self) -> int:  # pragma: no cover
        """Hash the dataclass in a safe way.

        Returns:
            A hash
        """
        return sum(hash(v) for v in asdict(self) if isinstance(v, Hashable))


def Body(
    *,
    media_type: str | RequestEncodingType = RequestEncodingType.JSON,
    examples: list[Example] | None = None,
    external_docs: ExternalDocumentation | None = None,
    content_encoding: str | None = None,
    default: Any = Empty,
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
    multipart_form_part_limit: int | None = None,
) -> Any:
    """Create an extended request body kwarg definition.

    Args:
        media_type: Defaults to RequestEncodingType.JSON.
        examples: A list of Example models.
        external_docs: A url pointing at external documentation for the given
            parameter.
        content_encoding: The content encoding of the value. Applicable on to string values. See
            OpenAPI 3.1 for details.
        default: A default value. If const is true, this value is required.
        title: String value used in the title section of the OpenAPI schema for the given
            parameter.
        description: String value used in the description section of the OpenAPI schema for the
            given parameter.
        const: A boolean flag dictating whether this parameter is a constant. If True, the value passed
            to the parameter must equal its default value. This also causes the OpenAPI const field to be populated with
            the default value.
        gt: Constrict value to be greater than a given float or int. Equivalent to
            exclusiveMinimum in the OpenAPI specification.
        ge: Constrict value to be greater or equal to a given float or int. Equivalent to
            minimum in the OpenAPI specification.
        lt: Constrict value to be less than a given float or int. Equivalent to
            exclusiveMaximum in the OpenAPI specification.
        le: Constrict value to be less or equal to a given float or int. Equivalent to maximum
            in the OpenAPI specification.
        multiple_of: Constrict value to a multiple of a given float or int. Equivalent to
            multipleOf in the OpenAPI specification.
        min_items: Constrict a set or a list to have a minimum number of items. Equivalent to
            minItems in the OpenAPI specification.
        max_items: Constrict a set or a list to have a maximum number of items. Equivalent to
            maxItems in the OpenAPI specification.
        min_length: Constrict a string or bytes value to have a minimum length. Equivalent to
            minLength in the OpenAPI specification.
        max_length: Constrict a string or bytes value to have a maximum length. Equivalent to
            maxLength in the OpenAPI specification.
        regex: A string representing a regex against which the given string will be matched.
            Equivalent to pattern in the OpenAPI specification.
        multipart_form_part_limit: The maximal number of allowed parts in a multipart/formdata request.
            This limit is intended to protect from DoS attacks.
    """
    return BodyKwarg(
        media_type=media_type,
        examples=examples,
        external_docs=external_docs,
        content_encoding=content_encoding,
        default=default,
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
        multipart_form_part_limit=multipart_form_part_limit,
    )


@dataclass(frozen=True)
class DependencyKwarg:
    """Data container representing a dependency."""

    default: Any = field(default=Empty)
    """A default value."""
    skip_validation: bool = field(default=False)
    """Flag dictating whether to skip validation."""

    def __hash__(self) -> int:
        """Hash the dataclass in a safe way.

        Returns:
            A hash
        """
        return sum(hash(v) for v in asdict(self) if isinstance(v, Hashable))


def Dependency(*, default: Any = Empty, skip_validation: bool = False) -> Any:
    """Create a dependency kwarg definition.

    Args:
        default: A default value to use in case a dependency is not provided.
        skip_validation: If `True` provided dependency values are not validated by signature model.
    """
    return DependencyKwarg(default=default, skip_validation=skip_validation)
