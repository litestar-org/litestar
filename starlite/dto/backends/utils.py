from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import get_origin

if TYPE_CHECKING:
    from typing import Any

__all__ = ("build_annotation_for_backend",)


def build_annotation_for_backend(annotation: Any, model: type[Any]) -> Any:
    """A helper to re-build a generic outer type with new inner type.

    Args:
        annotation: The original annotation on the handler signature
        model: The serde model for data transfer

    Returns:
        Annotation with new inner type if applicable.
    """
    origin = get_origin(annotation)
    if not origin:
        return model
    try:
        return origin[model]
    except TypeError:
        return annotation.copy_with((model,))
