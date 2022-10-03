from typing import Any, Dict, List, Optional, Union

from pydantic import validate_arguments
from pydantic.fields import Field, Undefined
from pydantic_openapi_schema.v3_1_0.example import Example
from pydantic_openapi_schema.v3_1_0.external_documentation import ExternalDocumentation

from starlite.constants import EXTRA_KEY_IS_DEPENDENCY, EXTRA_KEY_SKIP_VALIDATION
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
    """Creates a pydantic `FieldInfo` instance with an extra kwargs, used for
    both parameter parsing and OpenAPI schema generation.

    Args:
        value_type: `Undefined` by default.
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
    """Creates a pydantic `FieldInfo` instance with an extra kwargs, used for
    both parameter parsing and OpenAPI schema generation.

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
    """
    extra: Dict[str, Any] = {}
    extra.update(media_type=media_type)
    extra.update(examples=examples)
    extra.update(external_docs=external_docs)
    extra.update(content_encoding=content_encoding)
    return Field(
        default,
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
def Dependency(*, default: Any = Undefined, skip_validation: bool = False) -> Any:
    """Creates a pydantic `FieldInfo` instance with an extra kwargs, used for
    both parameter parsing and OpenAPI schema generation.

    Args:
        default: default value if dependency not provided.
        skip_validation: If `True` provided dependency values are not validated by signature model.
    """
    extra: Dict[str, Any] = {EXTRA_KEY_IS_DEPENDENCY: True, EXTRA_KEY_SKIP_VALIDATION: skip_validation}
    return Field(default, **extra)  # type: ignore[pydantic-field]
