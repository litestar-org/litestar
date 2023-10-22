from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.constants import UNDEFINED_SENTINELS
from litestar.types import Empty
from litestar.utils import is_class_and_subclass

# isort: off
try:
    from pydantic import v1 as pydantic_v1
    import pydantic as pydantic_v2
except ImportError:
    import pydantic as pydantic_v1  # type: ignore[no-redef]

    pydantic_v2 = Empty  # type: ignore[assignment]

except ImportError:  # noqa: B025  # pyright: ignore
    pydantic_v1 = Empty  # type: ignore[assignment]
    pydantic_v2 = Empty  # type: ignore[assignment]
# isort: on


if TYPE_CHECKING:
    from typing_extensions import TypeGuard

PYDANTIC_UNDEFINED_SENTINELS = set()

if pydantic_v1 is not Empty:  # type: ignore[comparison-overlap]
    PYDANTIC_UNDEFINED_SENTINELS.add(pydantic_v1.fields.Undefined)  # pyright: ignore
    if pydantic_v2 is not Empty:  # type: ignore[comparison-overlap]
        PYDANTIC_UNDEFINED_SENTINELS.add(pydantic_v2.fields.PydanticUndefined)  # type: ignore[attr-defined]

UNDEFINED_SENTINELS.update(PYDANTIC_UNDEFINED_SENTINELS)


def is_pydantic_model_class(
    annotation: Any,
) -> TypeGuard[type[pydantic_v1.BaseModel | pydantic_v2.BaseModel]]:  # pyright: ignore
    """Given a type annotation determine if the annotation is a subclass of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    if pydantic_v1 is not Empty:  # type: ignore[comparison-overlap]
        if pydantic_v2 is not Empty:  # type: ignore[comparison-overlap]
            return is_class_and_subclass(annotation, (pydantic_v1.BaseModel, pydantic_v2.BaseModel))
        return is_class_and_subclass(annotation, pydantic_v1.BaseModel)
    return False


def is_pydantic_model_instance(
    annotation: Any,
) -> TypeGuard[pydantic_v1.BaseModel | pydantic_v2.BaseModel]:  # pyright: ignore
    """Given a type annotation determine if the annotation is an instance of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    if pydantic_v1 is not Empty:  # type: ignore[comparison-overlap]
        if pydantic_v2 is not Empty:  # type: ignore[comparison-overlap]
            return isinstance(annotation, (pydantic_v1.BaseModel, pydantic_v2.BaseModel))
        return isinstance(annotation, pydantic_v1.BaseModel)
    return False


def is_pydantic_constrained_field(annotation: Any) -> Any:
    """Check if the given annotation is a constrained pydantic type.

    Args:
        annotation: A type annotation

    Returns:
        True if pydantic is installed and the type is a constrained type, otherwise False.
    """
    if pydantic_v1 is Empty:  # type: ignore[comparison-overlap]
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
    if pydantic_v1 is Empty:  # type: ignore[comparison-overlap]
        return False
    if pydantic_v2 is not Empty:  # type: ignore[comparison-overlap]
        return isinstance(obj, (pydantic_v1.fields.FieldInfo, pydantic_v2.fields.FieldInfo))
    return isinstance(obj, pydantic_v1.fields.FieldInfo)
