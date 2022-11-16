from typing import TYPE_CHECKING, Any, Dict, Iterable, Union

from anyio import create_task_group
from pydantic.fields import FieldInfo

from starlite.constants import EXTRA_KEY_IS_DEPENDENCY, EXTRA_KEY_SKIP_VALIDATION

if TYPE_CHECKING:
    from typing_extensions import TypeGuard

    from starlite.connection import Request, WebSocket
    from starlite.kwargs import Dependency, KwargsModel


def is_dependency_field(val: Any) -> "TypeGuard[FieldInfo]":
    """Determine if a value is a `FieldInfo` instance created via the `Dependency()` function.

    Args:
        val(Any): value to be tested

    Returns:
        `True` if `val` is `FieldInfo` created by [`Dependency()`][starlite.params.Dependency] function.
    """
    return isinstance(val, FieldInfo) and bool(val.extra.get(EXTRA_KEY_IS_DEPENDENCY))


def should_skip_dependency_validation(val: Any) -> bool:
    """Determine if a value is a `FieldInfo` instance created via the `Dependency()` function set with
    `skip_validation=True`.

    Args:
        val(Any): value to be tested

    Returns:
        `True` if `val` is `FieldInfo` created by [`Dependency()`][starlite.params.Dependency] function and
        `skip_validation=True` is set.
    """
    return is_dependency_field(val) and bool(val.extra.get(EXTRA_KEY_SKIP_VALIDATION))


async def _resolve_dependency_into_kwargs(
    model: "KwargsModel", dependency: "Dependency", connection: Union["WebSocket", "Request"], kwargs: Dict[str, Any]
) -> None:
    """Store the result of resolve_dependency in the kwargs."""
    kwargs[dependency.key] = await model.resolve_dependency(dependency=dependency, connection=connection, **kwargs)
