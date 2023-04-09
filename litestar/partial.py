from __future__ import annotations

from dataclasses import MISSING, fields, make_dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)

from typing_extensions import NotRequired, TypeAlias, TypedDict

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types.builtin_types import NoneType
from litestar.utils.predicates import (
    is_attrs_class,
    is_class_var,
    is_dataclass_class,
    is_pydantic_model_class,
    is_typed_dict,
)

if TYPE_CHECKING:
    import attrs
    import pydantic

__all__ = ("Partial",)


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


class Partial(Generic[T]):
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
            if is_pydantic_model_class(item):
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

        field_definitions: dict[str, tuple[Any, None]] = {}
        for field_name, field_type in get_type_hints(item).items():
            if is_class_var(field_type):
                continue
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
                field_definitions[field_name] = (Optional[field_type], None)
            else:
                field_definitions[field_name] = (field_type, None)

        cls._models[item] = pydantic.create_model(cls._create_partial_type_name(item), __base__=item, **field_definitions)  # type: ignore

    @classmethod
    def _create_partial_attrs_model(cls, item: type[attrs.AttrsInstance]) -> None:
        import attrs

        field_definitions: dict[str, Any] = {}
        for field_name, field_type in get_type_hints(item).items():
            if is_class_var(field_type):
                continue
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
                field_definitions[field_name] = Optional[field_type]
            else:
                field_definitions[field_name] = field_type

        cls._models[item] = attrs.define(
            type(
                cls._create_partial_type_name(item),
                (item,),
                {"__annotations__": field_definitions, **{k: None for k in field_definitions}},  # type: ignore[misc]
            )
        )

    @classmethod
    def _create_partial_dataclass(cls, item: type[DataclassProtocol]) -> None:
        """Receives a dataclass class and creates an all optional subclass of it.

        Args:
            item: A dataclass class.
        """
        field_definitions: list[tuple[str, type, Any]] = []
        dataclass_fields = {field.name: field for field in fields(item)}
        for field_name, field_type in get_type_hints(item).items():
            dataclass_field = dataclass_fields[field_name]
            default_value = (
                dataclass_field.default if dataclass_field.default is not MISSING else dataclass_field.default_factory
            )

            if is_class_var(field_type):
                field_definitions.append((field_name, field_type, default_value))
            elif not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
                field_definitions.append((field_name, Optional[field_type], None))  # type: ignore[arg-type]
            else:
                field_definitions.append((field_name, field_type, None))

        cls._models[item] = make_dataclass(
            cls_name=cls._create_partial_type_name(item),
            fields=field_definitions,
            bases=(item,),
        )

    @classmethod
    def _create_partial_typeddict(cls, item: "TypedDictClass") -> None:
        """Receives a typeddict class and creates a new type with all attributes ``Optional``.

        Args:
            item: A :class:`TypedDict <typing.TypeDict>` class.
        """
        field_definitions: dict[str, Any] = {}
        for field_name, field_type in get_type_hints(item).items():
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
                field_definitions[field_name] = NotRequired[Optional[field_type]]  # pyright: ignore
            else:
                field_definitions[field_name] = NotRequired[field_type]  # pyright: ignore
        cls._models[item] = TypedDict(cls._create_partial_type_name(item), field_definitions)  # type: ignore

    @staticmethod
    def _create_partial_type_name(item: SupportedTypes) -> str:
        return f"Partial{item.__name__}"
