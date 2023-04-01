from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable as CollectionsIterable
from dataclasses import is_dataclass
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Any,
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

from typing_extensions import (
    ParamSpec,
    TypeGuard,
    get_args,
    is_typeddict,
)

from litestar.types import DataclassProtocol, Empty
from litestar.types.builtin_types import UNION_TYPES, NoneType
from litestar.utils.typing import get_origin_or_inner_type

if TYPE_CHECKING:
    from litestar.types.builtin_types import (
        TypedDictClass,
    )

try:
    import pydantic
except ImportError:  # pragma: no cover
    pydantic = Empty  # type: ignore

try:
    import attrs
except ImportError:  # pragma: no cover
    attrs = Empty  # type: ignore


P = ParamSpec("P")
T = TypeVar("T")


def is_class_and_subclass(annotation: Any, t_type: type[T]) -> TypeGuard[type[T]]:
    """Return ``True`` if ``value`` is a ``class`` and is a subtype of ``t_type``.

    See https://github.com/starlite-api/litestar/issues/367

    Args:
        annotation: The value to check if is class and subclass of ``t_type``.
        t_type: Type used for :func:`issubclass` check of ``value``

    Returns:
        bool
    """
    origin = get_origin_or_inner_type(annotation)
    if not origin and not isclass(annotation):
        return False
    try:
        return issubclass(origin or annotation, t_type)
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
        or (get_origin_or_inner_type(annotation) in UNION_TYPES and Any in get_args(annotation))
    )


def is_union(annotation: Any) -> bool:
    """Given a type annotation determine if the annotation infers an optional union.

    Args:
        annotation: A type.

    Returns:
        A boolean determining whether the type is :data:`Union typing.Union>`.
    """
    return get_origin_or_inner_type(annotation) in UNION_TYPES


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
        get_origin_or_inner_type(annotation) in UNION_TYPES and NoneType in get_args(annotation)
    )


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


def is_typed_dict(annotation: Any) -> TypeGuard[TypedDictClass]:
    """Wrap :func:`typing.is_typeddict` in a :data:`typing.TypeGuard`.

    Args:
        annotation: tested to determine if instance or type of :class:`typing.TypedDict`.

    Returns:
        ``True`` if instance or type of ``TypedDict``.
    """
    return is_typeddict(annotation)


def is_pydantic_model_class(annotation: Any) -> "TypeGuard[type[pydantic.BaseModel]]":  # pyright: ignore
    """Given a type annotation determine if the annotation is a subclass of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    if pydantic is not Empty:  # type: ignore[comparison-overlap]
        return is_class_and_subclass(annotation, pydantic.BaseModel)  # pyright: ignore
    return False  # pragma: no cover


def is_pydantic_model_instance(annotation: Any) -> "TypeGuard[pydantic.BaseModel]":  # pyright: ignore
    """Given a type annotation determine if the annotation is an instance of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    if pydantic is not Empty:  # type: ignore[comparison-overlap]
        return isinstance(annotation, pydantic.BaseModel)  # pyright: ignore
    return False  # pragma: no cover


def is_attrs_class(annotation: Any) -> TypeGuard["attrs.AttrsInstance"]:  # pyright: ignore
    """Given a type annotation determine if the annotation is a class that includes an attrs attribute.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is an attrs class.
    """
    if attrs is not Empty:  # type: ignore[comparison-overlap]
        return attrs.has(annotation)  # pyright: ignore
    return False  # pragma: no cover
