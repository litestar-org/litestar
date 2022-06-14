from typing import AbstractSet, Any

from pydantic.fields import FieldInfo, Undefined

from starlite.exceptions import ImproperlyConfiguredException


def check_for_unprovided_dependency(
    key: str, field: Any, is_optional: bool, provided_dependency_names: AbstractSet[str], fn_name: str
) -> None:
    """
    Where a dependency has been explicitly marked using the ``Dependency`` function, it is a
    configuration error if that dependency has been defined without a default value, and it hasn't
    been provided to the handler.

    Raises ``ImproperlyConfiguredException`` where case is detected.
    """
    if is_optional:
        return
    if not isinstance(field, FieldInfo):
        return
    if not field.extra.get("is_dependency"):
        return
    if field.default is not Undefined:
        return
    if key not in provided_dependency_names:
        raise ImproperlyConfiguredException(
            f"Explicit dependency '{key}' for '{fn_name}' has no default value, or provided dependency."
        )
