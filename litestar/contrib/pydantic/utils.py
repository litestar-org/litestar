from __future__ import annotations

from pydantic import VERSION as PYDANTIC_VERSION
from typing_extensions import Any, get_type_hints

from litestar.utils.predicates import is_generic
from litestar.utils.typing import (
    _substitute_typevars,
    _zip,
    get_origin_or_inner_type,
    get_type_hints_with_generics_resolved,
    instantiable_type_mapping,
    unwrap_annotation,
    wrapper_type_set,
)

if PYDANTIC_VERSION.startswith("2"):
    # These utility functions are the same as the ones in litestar.utils.typing but this has to be
    # done due to this issue: https://github.com/pydantic/pydantic/issues/7837. This is only for
    # v2.

    def pydantic_unwrap_and_get_origin(annotation: Any) -> Any | None:
        origin = annotation.__pydantic_generic_metadata__["origin"]
        if origin in wrapper_type_set:
            inner, _, _ = unwrap_annotation(annotation)
            origin = get_origin_or_inner_type(inner)
        return instantiable_type_mapping.get(origin, origin)

    def pydantic_get_type_hints_with_generics_resolved(
        annotation: Any,
        globalns: dict[str, Any] | None = None,
        localns: dict[str, Any] | None = None,
        include_extras: bool = False,
    ) -> dict[str, Any]:
        origin = pydantic_unwrap_and_get_origin(annotation)
        if origin is None:
            type_hints = get_type_hints(annotation, globalns=globalns, localns=localns, include_extras=include_extras)
            typevar_map = {p: p for p in annotation.__pydantic_generic_metadata__["parameters"]}
        else:
            type_hints = get_type_hints(origin, globalns=globalns, localns=localns, include_extras=include_extras)
            args = annotation.__pydantic_generic_metadata__["args"]
            parameters = origin.__pydantic_generic_metadata__["parameters"]
            typevar_map = dict(_zip(parameters, args))  # type: ignore[operator]

        return {n: _substitute_typevars(type_, typevar_map) for n, type_ in type_hints.items()}

else:
    pydantic_unwrap_and_get_origin = get_origin_or_inner_type

    def pydantic_get_type_hints_with_generics_resolved(
        annotation: Any,
        globalns: dict[str, Any] | None = None,
        localns: dict[str, Any] | None = None,
        include_extras: bool = False,
    ) -> dict[str, Any]:
        if not is_generic(annotation):
            return get_type_hints(annotation, globalns=globalns, localns=localns, include_extras=include_extras)

        return get_type_hints_with_generics_resolved(annotation, globalns, localns, include_extras)


def pydantic_get_unwrapped_annotation_and_type_hints(annotation: Any) -> tuple[Any, dict[str, Any]]:
    """Get the unwrapped annotation and the type hints after resolving generics.

    Args:
        annotation: A type annotation.

    Returns:
        A tuple containing the unwrapped annotation and the type hints.
    """

    if is_generic(annotation):
        origin = pydantic_unwrap_and_get_origin(annotation)
        return origin or annotation, pydantic_get_type_hints_with_generics_resolved(annotation, include_extras=True)
    return annotation, get_type_hints(annotation, include_extras=True)
