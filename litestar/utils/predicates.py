from __future__ import annotations

from asyncio import iscoroutinefunction
from collections import defaultdict, deque
from collections.abc import Iterable as CollectionsIterable
from dataclasses import is_dataclass
from functools import partial
from inspect import isasyncgenfunction, isclass, isgeneratorfunction
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    DefaultDict,
    Deque,
    Dict,
    FrozenSet,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
)

from msgspec import Struct
from typing_extensions import (
    ParamSpec,
    TypeGuard,
    _AnnotatedAlias,
    get_args,
    is_typeddict,
)

from litestar.constants import UNDEFINED_SENTINELS
from litestar.types import Empty
from litestar.types.builtin_types import NoneType, UnionTypes
from litestar.utils.typing import get_origin_or_inner_type

if TYPE_CHECKING:
    from litestar.types.builtin_types import TypedDictClass
    from litestar.types.callable_types import AnyGenerator
    from litestar.types.protocols import DataclassProtocol

try:
    import pydantic
except ImportError:  # pragma: no cover
    pydantic = Empty  # type: ignore

try:
    import attrs
except ImportError:  # pragma: no cover
    attrs = Empty  # type: ignore

__all__ = (
    "is_annotated_type",
    "is_any",
    "is_async_callable",
    "is_attrs_class",
    "is_class_and_subclass",
    "is_class_var",
    "is_dataclass_class",
    "is_dataclass_instance",
    "is_generic",
    "is_mapping",
    "is_non_string_iterable",
    "is_non_string_sequence",
    "is_optional_union",
    "is_pydantic_constrained_field",
    "is_pydantic_model_class",
    "is_pydantic_model_instance",
    "is_struct_class",
    "is_sync_or_async_generator",
    "is_typed_dict",
    "is_undefined_sentinel",
    "is_union",
)

P = ParamSpec("P")
T = TypeVar("T")


def is_async_callable(value: Callable[P, T]) -> TypeGuard[Callable[P, Awaitable[T]]]:
    """Extend :func:`asyncio.iscoroutinefunction` to additionally detect async :func:`functools.partial` objects and
    class instances with ``async def __call__()`` defined.

    Args:
        value: Any

    Returns:
        Bool determining if type of ``value`` is an awaitable.
    """
    while isinstance(value, partial):
        value = value.func  # type: ignore[unreachable]

    return iscoroutinefunction(value) or (
        callable(value) and iscoroutinefunction(value.__call__)  # type: ignore[operator]
    )


def is_dataclass_instance(obj: Any) -> TypeGuard[DataclassProtocol]:
    """Check if an object is a dataclass instance.

    Args:
        obj: An object to check.

    Returns:
        True if the object is a dataclass instance.
    """
    return hasattr(type(obj), "__dataclass_fields__")


def is_dataclass_class(annotation: Any) -> TypeGuard[type[DataclassProtocol]]:
    """Wrap :func:`is_dataclass <dataclasses.is_dataclass>` in a :data:`typing.TypeGuard`.

    Args:
        annotation: tested to determine if instance or type of :class:`dataclasses.dataclass`.

    Returns:
        ``True`` if instance or type of ``dataclass``.
    """
    try:
        return isclass(annotation) and is_dataclass(annotation)
    except TypeError:  # pragma: no cover
        return False


def is_class_and_subclass(annotation: Any, type_or_type_tuple: type[T] | tuple[type[T], ...]) -> TypeGuard[type[T]]:
    """Return ``True`` if ``value`` is a ``class`` and is a subtype of ``t_type``.

    See https://github.com/litestar-org/litestar/issues/367

    Args:
        annotation: The value to check if is class and subclass of ``t_type``.
        type_or_type_tuple: Type used for :func:`issubclass` check of ``value``

    Returns:
        bool
    """
    origin = get_origin_or_inner_type(annotation)
    if not origin and not isclass(annotation):
        return False
    try:
        return issubclass(origin or annotation, type_or_type_tuple)
    except TypeError:  # pragma: no cover
        return False


def is_generic(annotation: Any) -> bool:
    """Given a type annotation determine if the annotation is a generic class.

    Args:
    annotation: A type.

    Returns:
        True if the annotation is a subclass of :data:`Generic <typing.Generic>` otherwise ``False``.
    """
    return is_class_and_subclass(annotation, Generic)  # type: ignore


def is_mapping(annotation: Any) -> TypeGuard[Mapping[Any, Any]]:
    """Given a type annotation determine if the annotation is a mapping type.

    Args:
    annotation: A type.

    Returns:
        A typeguard determining whether the type can be cast as :class:`Mapping <typing.Mapping>`.
    """
    _type = get_origin_or_inner_type(annotation) or annotation
    return isclass(_type) and issubclass(_type, (dict, defaultdict, DefaultDict, Mapping))


def is_non_string_iterable(annotation: Any) -> TypeGuard[Iterable[Any]]:
    """Given a type annotation determine if the annotation is an iterable.

    Args:
    annotation: A type.

    Returns:
        A typeguard determining whether the type can be cast as :class:`Iterable <typing.Iterable>` that is not a string.
    """
    origin = get_origin_or_inner_type(annotation)
    if not origin and not isclass(annotation):
        return False
    try:
        return not issubclass(origin or annotation, (str, bytes)) and (
            issubclass(origin or annotation, (Iterable, CollectionsIterable, Dict, dict, Mapping))
            or is_non_string_sequence(annotation)
        )
    except TypeError:  # pragma: no cover
        return False


def is_non_string_sequence(annotation: Any) -> TypeGuard[Sequence[Any]]:
    """Given a type annotation determine if the annotation is a sequence.

    Args:
    annotation: A type.

    Returns:
        A typeguard determining whether the type can be cast as :class`Sequence <typing.Sequence>` that is not a string.
    """
    origin = get_origin_or_inner_type(annotation)
    if not origin and not isclass(annotation):
        return False
    try:
        return not issubclass(origin or annotation, (str, bytes)) and issubclass(
            origin or annotation,
            (  # type: ignore
                Tuple,
                List,
                Set,
                FrozenSet,
                Deque,
                Sequence,
                list,
                tuple,
                deque,
                set,
                frozenset,
            ),
        )
    except TypeError:  # pragma: no cover
        return False


def is_any(annotation: Any) -> TypeGuard[Any]:
    """Given a type annotation determine if the annotation is Any.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`Any <typing.Any>`.
    """
    return (
        annotation is Any
        or getattr(annotation, "_name", "") == "typing.Any"
        or (get_origin_or_inner_type(annotation) in UnionTypes and Any in get_args(annotation))
    )


def is_union(annotation: Any) -> bool:
    """Given a type annotation determine if the annotation infers an optional union.

    Args:
        annotation: A type.

    Returns:
        A boolean determining whether the type is :data:`Union typing.Union>`.
    """
    return get_origin_or_inner_type(annotation) in UnionTypes


def is_optional_union(annotation: Any) -> TypeGuard[Any | None]:
    """Given a type annotation determine if the annotation infers an optional union.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`Union typing.Union>` with a
            None value or :data:`Optional <typing.Optional>` which is equivalent.
    """
    origin = get_origin_or_inner_type(annotation)
    return origin is Optional or (
        get_origin_or_inner_type(annotation) in UnionTypes and NoneType in get_args(annotation)
    )


def is_typed_dict(annotation: Any) -> TypeGuard[TypedDictClass]:
    """Wrap :func:`typing.is_typeddict` in a :data:`typing.TypeGuard`.

    Args:
        annotation: tested to determine if instance or type of :class:`typing.TypedDict`.

    Returns:
        ``True`` if instance or type of ``TypedDict``.
    """
    return is_typeddict(annotation)


def is_pydantic_model_class(annotation: Any) -> TypeGuard[type[pydantic.BaseModel]]:  # pyright: ignore
    """Given a type annotation determine if the annotation is a subclass of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    if pydantic is not Empty:  # type: ignore[comparison-overlap]
        return is_class_and_subclass(annotation, pydantic.BaseModel)  # pyright: ignore
    return False  # pragma: no cover


def is_pydantic_model_instance(annotation: Any) -> TypeGuard[pydantic.BaseModel]:  # pyright: ignore
    """Given a type annotation determine if the annotation is an instance of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    if pydantic is not Empty:  # type: ignore[comparison-overlap]
        return isinstance(annotation, pydantic.BaseModel)  # pyright: ignore
    return False  # pragma: no cover


def is_attrs_class(annotation: Any) -> TypeGuard[type[attrs.AttrsInstance]]:  # pyright: ignore
    """Given a type annotation determine if the annotation is a class that includes an attrs attribute.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is an attrs class.
    """
    return attrs.has(annotation) if attrs is not Empty else False  # type: ignore[comparison-overlap]


def is_pydantic_constrained_field(
    annotation: Any,
) -> Any:
    """Check if the given annotation is a constrained pydantic type.

    Args:
        annotation: A type annotation

    Returns:
        True if pydantic is installed and the type is a constrained type, otherwise False.
    """
    try:
        # removed in pydantic v2
        # so this will raise an ImportError - which is expected.
        from pydantic import (
            ConstrainedBytes,
            ConstrainedDate,
            ConstrainedDecimal,
            ConstrainedFloat,
            ConstrainedFrozenSet,
            ConstrainedInt,
            ConstrainedList,
            ConstrainedSet,
            ConstrainedStr,
        )

        return any(
            is_class_and_subclass(annotation, constrained_type)  # type: ignore[arg-type]
            for constrained_type in (
                ConstrainedBytes,
                ConstrainedDate,
                ConstrainedDecimal,
                ConstrainedFloat,
                ConstrainedFrozenSet,
                ConstrainedInt,
                ConstrainedList,
                ConstrainedSet,
                ConstrainedStr,
            )
        )
    except ImportError:
        return False


def is_struct_class(annotation: Any) -> TypeGuard[type[Struct]]:
    """Check if the given annotation is a :class:`Struct <msgspec.Struct>` type.

    Args:
        annotation: A type annotation

    Returns:
        A typeguard for :class:`Struct <msgspec.Struct>`.
    """
    return is_class_and_subclass(annotation, Struct)


def is_class_var(annotation: Any) -> bool:
    """Check if the given annotation is a ClassVar.

    Args:
        annotation: A type annotation

    Returns:
        A boolean.
    """
    annotation = get_origin_or_inner_type(annotation) or annotation
    return annotation is ClassVar


def is_sync_or_async_generator(obj: Any) -> TypeGuard[AnyGenerator]:
    """Check if the given annotation is a sync or async generator.

    Args:
        obj: type to be tested for sync or async generator.

    Returns:
        A boolean.
    """
    return isgeneratorfunction(obj) or isasyncgenfunction(obj)


def is_annotated_type(annotation: Any) -> bool:
    """Check if the given annotation is an Annotated.

    Args:
        annotation: A type annotation

    Returns:
        A boolean.
    """
    return isinstance(annotation, _AnnotatedAlias) and getattr(annotation, "__args__", None) is not None


def is_undefined_sentinel(value: Any) -> bool:
    """Check if the given value is the undefined sentinel.

    Args:
        value: A value to be tested for undefined sentinel.

    Returns:
        A boolean.
    """
    return any(v is value for v in UNDEFINED_SENTINELS)
