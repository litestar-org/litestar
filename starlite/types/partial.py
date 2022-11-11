from dataclasses import MISSING
from dataclasses import Field as DataclassField
from dataclasses import dataclass
from inspect import getmro
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Optional,
    Tuple,
    Type,
    TypeVar,
    get_type_hints,
)

from pydantic import BaseModel, create_model
from pydantic.typing import is_classvar
from typing_extensions import TypedDict, get_args

from starlite.exceptions import ImproperlyConfiguredException
from starlite.types.builtin_types import NoneType
from starlite.utils.predicates import (
    is_class_and_subclass,
    is_dataclass_class_typeguard,
    is_typeddict_typeguard,
)

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore

if TYPE_CHECKING:
    from typing import TypeAlias, Union  # noqa: F401  # nopycln: import

    from starlite.types.builtin_types import DataclassClass, TypedDictClass

T = TypeVar("T")

SupportedTypes: "TypeAlias" = "Union[DataclassClass, Type[BaseModel], TypedDictClass]"
"""Types that are supported by [`Partial`][starlite.types.partial.Partial]"""


class Partial(Generic[T]):
    """Type generation for PATCH routes.

    Partial is a special typing helper that takes a generic T, which must be a
    [`TypedDict`][typing.TypedDict], dataclass or pydantic model class, and
    returns to static type checkers a version of this T in which all fields -
    and nested fields - are optional.
    """

    _models: Dict[SupportedTypes, SupportedTypes] = {}

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        """Take a pydantic model class, [`TypedDict`][typing.TypedDict] or a dataclass and return an all optional
        version of that class.

        Args:
            item: A pydantic model, [`TypedDict`][typing.TypedDict] or dataclass class.

        Returns:
            A pydantic model, [`TypedDict`][typing.TypedDict], or dataclass.
        """
        if item not in cls._models:
            if is_class_and_subclass(item, BaseModel):
                cls._create_partial_pydantic_model(item=item)
            elif is_dataclass_class_typeguard(item):
                cls._create_partial_dataclass(item=item)
            elif is_typeddict_typeguard(item):
                cls._create_partial_typeddict(item=item)
            else:
                raise ImproperlyConfiguredException(
                    "The type argument T passed to Partial[T] must be a `TypedDict`, dataclass or pydantic model class"
                )

        return cls._models[item]  # type:ignore[return-value]

    @classmethod
    def _create_partial_pydantic_model(cls, item: Type[BaseModel]) -> None:
        """Receives a pydantic model class and creates an all optional subclass of it.

        Args:
            item: A pydantic model class.
        """
        field_definitions: Dict[str, Tuple[Any, None]] = {}
        for field_name, field_type in get_type_hints(item).items():
            if is_classvar(field_type):
                continue
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
                field_definitions[field_name] = (Optional[field_type], None)
            else:
                field_definitions[field_name] = (field_type, None)

        cls._models[item] = create_model(cls._create_partial_type_name(item), __base__=item, **field_definitions)  # type: ignore

    @classmethod
    def _create_partial_dataclass(cls, item: "DataclassClass") -> None:
        """Receives a dataclass class and creates an all optional subclass of it.

        Args:
            item: A dataclass class.
        """
        fields: Dict[str, DataclassField] = cls._create_optional_field_map(item)
        partial_type: "DataclassClass" = dataclass(
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
        """Receives a typeddict class and creates a new type with all attributes `Optional`.

        Args:
            item: A [`TypedDict`][typing.TypeDict] class.
        """
        type_hints: Dict[str, Any] = {}
        for key_name, value_type in get_type_hints(item).items():
            if NoneType in get_args(value_type):
                type_hints[key_name] = value_type
                continue
            type_hints[key_name] = Optional[value_type]
        type_name = cls._create_partial_type_name(item)
        cls._models[item] = TypedDict(type_name, type_hints, total=False)  # type:ignore

    @staticmethod
    def _create_optional_field_map(item: "DataclassClass") -> Dict[str, DataclassField]:
        """Create a map of field name to optional dataclass Fields for a given dataclass.

        Args:
            item: A dataclass class.

        Returns:
            A map of field name to optional dataclass fields.
        """
        fields: Dict[str, DataclassField] = {}
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
