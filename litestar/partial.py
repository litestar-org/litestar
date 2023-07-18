from __future__ import annotations

from dataclasses import make_dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
)

import msgspec
from typing_extensions import TypeAlias, TypedDict, get_type_hints

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types.builtin_types import NoneType
from litestar.utils import warn_deprecation
from litestar.utils.predicates import (
    is_attrs_class,
    is_class_var,
    is_dataclass_class,
    is_pydantic_model_class,
    is_struct_class,
    is_typed_dict,
)

if TYPE_CHECKING:
    import attrs
    import pydantic

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore

if TYPE_CHECKING:
    from litestar.types import DataclassProtocol
    from litestar.types.builtin_types import TypedDictClass

T = TypeVar("T")

SupportedTypes: TypeAlias = "Union[Type[DataclassProtocol], Type[pydantic.BaseModel], TypedDictClass]"
"""Types that are supported by :class:`Partial <litestar.types.partial.Partial>`"""


def _create_partial_type_name(item: SupportedTypes) -> str:
    return f"Partial{item.__name__}"


def _extract_type_hints(item: Any) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (field_name, field_type)
        for field_name, field_type in get_type_hints(item, include_extras=True).items()
        if not is_class_var(field_type)
    )


class _Partial(Generic[T]):
    """Partial is a special typing helper that takes a generic T, and
    returns to static type checkers a version of this T in which all fields -
    and nested fields - are optional.
    """

    _models: dict[SupportedTypes, SupportedTypes] = {}

    def __class_getitem__(cls, item: type[T]) -> type[T]:
        """Take a pydantic model class, :class:`TypedDict <typing.TypedDict>` or a dataclass and return an all optional
        version of that class.

        Args:
            item: A pydantic model, :class:`TypedDict <typing.TypedDict>` or dataclass class.

        Returns:
            A pydantic model, :class:`TypedDict <typing.TypedDict>`, or dataclass.
        """
        if item not in cls._models:
            if is_struct_class(item):
                cls._create_partial_struct(item=item)
            elif is_pydantic_model_class(item):
                cls._create_partial_pydantic_model(item=item)
            elif is_attrs_class(item):
                cls._create_partial_attrs_model(item=item)
            elif is_dataclass_class(item):
                cls._create_partial_dataclass(item=item)
            elif is_typed_dict(item):
                cls._create_partial_typeddict(item=item)
            else:
                raise ImproperlyConfiguredException(
                    "The type argument T passed to Partial[T] must be a `TypedDict`, dataclass or pydantic model class"
                )

        return cls._models[item]  # type:ignore[return-value]

    @classmethod
    def _create_partial_pydantic_model(cls, item: type[pydantic.BaseModel]) -> None:
        """Receives a pydantic model class and creates an all optional subclass of it.

        Args:
            item: A pydantic model class.
        """
        import pydantic

        field_definitions: dict[str, tuple[Any, None]] = {
            field_name: (Optional[field_type], None)
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__
            else (field_type, None)
            for field_name, field_type in _extract_type_hints(item)
        }
        cls._models[item] = pydantic.create_model(
            _create_partial_type_name(item), __base__=item, **field_definitions  # pyright: ignore
        )  # type: ignore

    @classmethod
    def _create_partial_attrs_model(cls, item: type[attrs.AttrsInstance]) -> None:
        import attrs

        field_definitions: dict[str, Any] = {
            field_name: Optional[field_type]
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__
            else field_type
            for field_name, field_type in _extract_type_hints(item)
        }
        cls._models[item] = attrs.define(
            type(
                _create_partial_type_name(item),
                (item,),
                {"__annotations__": field_definitions, **{k: None for k in field_definitions}},
            )
        )

    @classmethod
    def _create_partial_dataclass(cls, item: type[DataclassProtocol]) -> None:
        """Receives a dataclass class and creates an all optional subclass of it.

        Args:
            item: A dataclass class.
        """
        field_definitions: list[tuple[str, type, Any]] = []
        for field_name, field_type in _extract_type_hints(item):
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
                field_definitions.append((field_name, Optional[field_type], None))  # type: ignore[arg-type]
            else:
                field_definitions.append((field_name, field_type, None))
        cls._models[item] = make_dataclass(
            cls_name=_create_partial_type_name(item),
            fields=field_definitions,
            bases=(item,),
        )

    @classmethod
    def _create_partial_typeddict(cls, item: TypedDictClass) -> None:
        """Receives a typeddict class and creates a new type with all attributes ``Optional``.

        Args:
            item: A :class:`TypedDict <typing.TypeDict>` class.
        """
        field_definitions: dict[str, Any] = {
            field_name: Optional[field_type]
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__
            else field_type
            for field_name, field_type in _extract_type_hints(item)
        }
        cls._models[item] = TypedDict(_create_partial_type_name(item), field_definitions, total=False)  # type: ignore

    @classmethod
    def _create_partial_struct(cls, item: type[msgspec.Struct]) -> None:
        """Receives a :class:`Struct <msgspec.Struct> class and creates a new type with all attributes ``Optional``.

        Args:
            item: A :class:`Struct <msgspec.Struct>` class.
        """
        field_definitions: list[tuple[str, type, Any]] = []
        for field_name, field_type in _extract_type_hints(item):
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
                field_definitions.append((field_name, Optional[field_type], None))  # type: ignore[arg-type]
            else:
                field_definitions.append((field_name, field_type, None))
        cls._models[item] = msgspec.defstruct(
            name=_create_partial_type_name(item),
            fields=field_definitions,
            bases=(item,),
        )


def __getattr__(attr_name: str) -> object:
    if "Partial" in attr_name:
        warn_deprecation(
            deprecated_name="litestar.partial.Partial",
            version="2.0b3",
            kind="class",
            removal_in="2.0",
            info="the 'Partial' class is deprecated, please use a partial DTO instead",
        )

        globals()[attr_name] = _Partial
        return _Partial
    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
