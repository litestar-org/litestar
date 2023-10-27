from __future__ import annotations

from typing import TYPE_CHECKING, Any

from typing_extensions import get_type_hints

from litestar.types import Empty
from litestar.utils import is_class_and_subclass
from litestar.utils.predicates import is_generic
from litestar.utils.typing import (
    _substitute_typevars,
    get_origin_or_inner_type,
    get_type_hints_with_generics_resolved,
    instantiable_type_mapping,
    unwrap_annotation,
    wrapper_type_set,
)

# isort: off
try:
    from pydantic import v1 as pydantic_v1
    import pydantic as pydantic_v2
except ImportError:
    try:
        import pydantic as pydantic_v1  # type: ignore[no-redef]

        pydantic_v2 = Empty  # type: ignore[assignment]

    except ImportError:  # pyright: ignore
        pydantic_v1 = Empty  # type: ignore[assignment]
        pydantic_v2 = Empty  # type: ignore[assignment]
# isort: on


if TYPE_CHECKING:
    from typing_extensions import TypeGuard


def is_pydantic_model_class(
    annotation: Any,
) -> TypeGuard[type[pydantic_v1.BaseModel | pydantic_v2.BaseModel]]:  # pyright: ignore
    """Given a type annotation determine if the annotation is a subclass of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    if pydantic_v1 is Empty:  # type: ignore[comparison-overlap] # pragma: no cover
        return False

    if pydantic_v2 is Empty:  # type: ignore[comparison-overlap] # pragma: no cover
        return is_class_and_subclass(annotation, pydantic_v1.BaseModel)

    return is_class_and_subclass(annotation, (pydantic_v1.BaseModel, pydantic_v2.BaseModel))


def is_pydantic_model_instance(
    annotation: Any,
) -> TypeGuard[pydantic_v1.BaseModel | pydantic_v2.BaseModel]:  # pyright: ignore
    """Given a type annotation determine if the annotation is an instance of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    if pydantic_v1 is Empty:  # type: ignore[comparison-overlap] # pragma: no cover
        return False

    if pydantic_v2 is Empty:  # type: ignore[comparison-overlap] # pragma: no cover
        return isinstance(annotation, pydantic_v1.BaseModel)

    return isinstance(annotation, (pydantic_v1.BaseModel, pydantic_v2.BaseModel))


def is_pydantic_constrained_field(annotation: Any) -> Any:
    """Check if the given annotation is a constrained pydantic type.

    Args:
        annotation: A type annotation

    Returns:
        True if pydantic is installed and the type is a constrained type, otherwise False.
    """
    if pydantic_v1 is Empty:  # type: ignore[comparison-overlap] # pragma: no cover
        return False

    return any(
        is_class_and_subclass(annotation, constrained_type)  # pyright: ignore
        for constrained_type in (
            pydantic_v1.ConstrainedBytes,
            pydantic_v1.ConstrainedDate,
            pydantic_v1.ConstrainedDecimal,
            pydantic_v1.ConstrainedFloat,
            pydantic_v1.ConstrainedFrozenSet,
            pydantic_v1.ConstrainedInt,
            pydantic_v1.ConstrainedList,
            pydantic_v1.ConstrainedSet,
            pydantic_v1.ConstrainedStr,
        )
    )


def is_pydantic_field_info(
    obj: Any,
) -> TypeGuard[pydantic_v1.fields.FieldInfo | pydantic_v2.fields.FieldInfo]:  # pyright: ignore
    if pydantic_v1 is Empty:  # type: ignore[comparison-overlap] # pragma: no cover
        return False

    if pydantic_v2 is Empty:  # type: ignore[comparison-overlap] # pragma: no cover
        return isinstance(obj, pydantic_v1.fields.FieldInfo)

    return isinstance(obj, (pydantic_v1.fields.FieldInfo, pydantic_v2.fields.FieldInfo))


def pydantic_unwrap_and_get_origin(annotation: Any) -> Any | None:
    if pydantic_v2 is Empty or is_class_and_subclass(annotation, pydantic_v1.BaseModel):  # type: ignore[comparison-overlap]
        return get_origin_or_inner_type(annotation)

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
    if pydantic_v2 is Empty or is_class_and_subclass(annotation, pydantic_v1.BaseModel):  # type: ignore[comparison-overlap]
        return get_type_hints_with_generics_resolved(annotation)

    origin = pydantic_unwrap_and_get_origin(annotation)
    if origin is None:
        type_hints = get_type_hints(annotation, globalns=globalns, localns=localns, include_extras=include_extras)
        typevar_map = {p: p for p in annotation.__pydantic_generic_metadata__["parameters"]}
    else:
        type_hints = get_type_hints(origin, globalns=globalns, localns=localns, include_extras=include_extras)
        args = annotation.__pydantic_generic_metadata__["args"]
        parameters = origin.__pydantic_generic_metadata__["parameters"]
        typevar_map = dict(zip(parameters, args))

    return {n: _substitute_typevars(type_, typevar_map) for n, type_ in type_hints.items()}


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


def is_pydantic_2_model(
    obj: type[pydantic_v1.BaseModel | pydantic_v2.BaseModel],  # pyright: ignore
) -> TypeGuard[pydantic_v2.BaseModel]:  # pyright: ignore
    return issubclass(obj, pydantic_v2.BaseModel)  # pyright: ignore
