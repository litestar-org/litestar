from __future__ import annotations

from dataclasses import MISSING, dataclass
from dataclasses import Field as DataclassField
from inspect import getmro
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

from typing_extensions import TypeAlias, TypedDict, get_args

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

        fields: dict[str, Any] = {}
        for field_name, field_type in get_type_hints(item).items():
            if is_class_var(field_type):
                continue
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
                fields[field_name] = Optional[field_type]
            else:
                fields[field_name] = field_type

        cls._models[item] = attrs.define(
            type(
                cls._create_partial_type_name(item),
                (item,),
                {"__annotations__": fields, **{k: None for k in fields}},  # type: ignore[misc]
            )
        )

    @classmethod
    def _create_partial_dataclass(cls, item: type[DataclassProtocol]) -> None:
        """Receives a dataclass class and creates an all optional subclass of it.

        Args:
            item: A dataclass class.
        """
        fields: dict[str, DataclassField] = cls._create_optional_field_map(item)
        partial_type: "type[DataclassProtocol]" = dataclass(
            type(cls._create_partial_type_name(item), (item,), {"__dataclass_fields__": fields})
        )
        annotated_ancestors = [a for a in getmro(partial_type) if hasattr(a, "__annotations__")]
        for ancestor in annotated_ancestors:
            for field_name, annotation in ancestor.__annotations__.items():
                if not isinstance(annotation, GenericAlias) or NoneType not in annotation.__args__:
                    partial_type.__annotations__[field_name] = Optional[annotation]
                else:
                    partial_type.__annotations__[field_name] = annotation

        cls._models[item] = partial_type

    @classmethod
    def _create_partial_typeddict(cls, item: "TypedDictClass") -> None:
        """Receives a typeddict class and creates a new type with all attributes ``Optional``.

        Args:
            item: A :class:`TypedDict <typing.TypeDict>` class.
        """
        type_hints: dict[str, Any] = {}
        for key_name, value_type in get_type_hints(item).items():
            if NoneType in get_args(value_type):
                type_hints[key_name] = value_type
                continue
            type_hints[key_name] = Optional[value_type]
        cls._models[item] = TypedDict(cls._create_partial_type_name(item), type_hints, total=False)  # type:ignore

    @staticmethod
    def _create_optional_field_map(item: type[DataclassProtocol]) -> dict[str, DataclassField]:
        """Create a map of field name to optional dataclass Fields for a given dataclass.

        Args:
            item: A dataclass class.

        Returns:
            A map of field name to optional dataclass fields.
        """
        fields: dict[str, DataclassField] = {}
        # https://github.com/python/typing/discussions/1056
        for field_name, dataclass_field in item.__dataclass_fields__.items():  # pyright:ignore
            if not isinstance(dataclass_field.type, GenericAlias) or NoneType not in dataclass_field.type.__args__:
                dataclass_field.type = Optional[dataclass_field.type]
            if dataclass_field.default_factory is MISSING:
                dataclass_field.default = None if dataclass_field.default is MISSING else dataclass_field.default
            fields[field_name] = dataclass_field
        return fields

    @staticmethod
    def _create_partial_type_name(item: SupportedTypes) -> str:
        return f"Partial{item.__name__}"
