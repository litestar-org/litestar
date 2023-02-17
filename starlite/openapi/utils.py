import re
from typing import TYPE_CHECKING

from starlite.exceptions import ImproperlyConfiguredException
from starlite.openapi.enums import OpenAPIType

if TYPE_CHECKING:
    from starlite.signature.models import SignatureField

CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")


def pascal_case_to_text(string: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'."""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, string)).strip()


def get_openapi_type_for_complex_type(field: "SignatureField") -> "OpenAPIType":
    """We are dealing with complex types in this case.

    The problem here is that the Python typing system is too crude to define OpenAPI objects properly.
    """
    if field.is_mapping:
        return OpenAPIType.OBJECT
    if field.is_non_string_sequence or field.is_non_string_iterable:
        return OpenAPIType.ARRAY

    raise ImproperlyConfiguredException(  # pragma: no cover
        f"Parameter '{field.name}' with type '{field.field_type}' could not be mapped to an Open API type. "
        f"This can occur if a user-defined generic type is resolved as a parameter. If '{field.name}' should "
        "not be documented as a parameter, annotate it using the `Dependency` function, e.g., "
        f"`{field.name}: ... = Dependency(...)`."
    )
