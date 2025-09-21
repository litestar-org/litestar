from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar.openapi.spec import Example

__all__ = ("ResponseHeader",)


@dataclass
class ResponseHeader:
    """Container type for a response header."""

    name: str
    """Header name"""

    documentation_only: bool = False
    """Defines the ResponseHeader instance as for OpenAPI documentation purpose only."""

    value: str | None = None
    """Value to set for the response header."""

    description: str | None = None
    """A brief description of the parameter. This could contain examples of
    use.

    [CommonMark syntax](https://spec.commonmark.org/) MAY be used for
    rich text representation.
    """

    required: bool = False
    """Determines whether this parameter is mandatory.

    If the [parameter location](https://spec.openapis.org/oas/v3.1.0#parameterIn) is `"path"`, this property is **REQUIRED** and its value MUST be `true`.
    Otherwise, the property MAY be included and its default value is `false`.
    """

    deprecated: bool = False
    """Specifies that a parameter is deprecated and SHOULD be transitioned out
    of usage.

    Default value is `false`.
    """

    style: str | None = None
    """Describes how the parameter value will be serialized depending on the
    type of the parameter value. Default values (based on value of `in`):

    - for `query` - `form`;
    - for `path` - `simple`;
    - for `header` - `simple`;
    - for `cookie` - `form`.
    """

    explode: bool | None = None
    """When this is true, parameter values of type `array` or `object` generate
    separate parameters for each value of the array or key-value pair of the
    map.

    For other types of parameters this property has no effect.
    When [style](https://spec.openapis.org/oas/v3.1.0#parameterStyle) is `form`, the default value is `true`.
    For all other styles, the default value is `false`.
    """

    example: Any | None = None
    """Example of the parameter's potential value.

    The example SHOULD match the specified schema and encoding
    properties if present. The `example` field is mutually exclusive of
    the `examples` field. Furthermore, if referencing a `schema` that
    contains an example, the `example` value SHALL _override_ the
    example provided by the schema. To represent examples of media types
    that cannot naturally be represented in JSON or YAML, a string value
    can contain the example with escaping where necessary.
    """

    examples: dict[str, Example] | None = None
    """Examples of the parameter's potential value. Each example SHOULD contain
    a value in the correct format as specified in the parameter encoding. The
    `examples` field is mutually exclusive of the `example` field. Furthermore,
    if referencing a `schema` that contains an example, the `examples` value
    SHALL _override_ the example provided by the schema.

    For more complex scenarios, the [content](https://spec.openapis.org/oas/v3.1.0#parameterContent) property
    can define the media type and schema of the parameter.
    A parameter MUST contain either a `schema` property, or a `content` property, but not both.
    When `example` or `examples` are provided in conjunction with the `schema` object,
    the example MUST follow the prescribed serialization strategy for the parameter.
    """

    def __post_init__(self) -> None:
        """Ensure that either value is set or the instance is for documentation_only."""
        if not self.documentation_only and self.value is None:
            raise ImproperlyConfiguredException("value must be set if documentation_only is false")

    def __hash__(self) -> int:
        return hash(self.name)
