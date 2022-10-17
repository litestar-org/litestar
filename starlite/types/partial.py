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
    Union,
    get_type_hints,
)

from pydantic import BaseModel, create_model
from typing_extensions import TypedDict

from starlite.exceptions import ImproperlyConfiguredException
from starlite.utils.predicates import (
    is_class_and_subclass,
    is_dataclass_type_typeguard,
    is_typeddict_typeguard,
)

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore

if TYPE_CHECKING:
    from starlite.types.builtin_types import DataclassType

T = TypeVar("T")


class Partial(Generic[T]):
    """Type generation for PATCH routes.

    Partial is a special typing helper that takes a generic T, which must be a
    `TypedDict`, dataclass or pydantic model class, and returns to static type
    checkers a version of this T in which all fields - and nested fields - are
    optional.
    """

    _models: Dict[Union["DataclassType", Type[T]], Type[T]] = {}

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        """Takes a pydantic model class, `TypedDict` or a dataclass and returns
        an all optional version of that class.

        Args:
            item: A pydantic model, `TypedDict` or dataclass class.

        Returns:
            A pydantic model, `TypedDict`, or dataclass.
        """

        if item not in cls._models:
            if is_class_and_subclass(item, BaseModel):
                cls._create_partial_pydantic_model(item=item)
            elif is_dataclass_type_typeguard(item):
                cls._create_partial_dataclass(item=item)
            elif is_typeddict_typeguard(item):
                cls._create_partial_typeddict(item=item)
            else:
                raise ImproperlyConfiguredException(
                    "The type argument T passed to Partial[T] must be a `TypedDict`, dataclass or pydantic model class"
                )

        return cls._models[item]  # pyright: ignore

    @classmethod
    def _create_partial_pydantic_model(cls, item: Type[BaseModel]) -> None:
        """Receives a pydantic model class and creates an all optional subclass
        of it.

        Args:
            item: A pydantic model class.
        """
        field_definitions: Dict[str, Tuple[Any, None]] = {}
        for field_name, field_type in get_type_hints(item).items():
            if not isinstance(field_type, GenericAlias) or type(None) not in field_type.__args__:
                field_definitions[field_name] = (Optional[field_type], None)
            else:
                field_definitions[field_name] = (field_type, None)

        cls._models[item] = create_model(f"Partial{item.__name__}", __base__=item, **field_definitions)  # type: ignore

    @classmethod
    def _create_partial_dataclass(cls, item: "DataclassType") -> None:
        """Receives a dataclass class and creates an all optional subclass of
        it.

        Args:
            item: A dataclass class.
        """
        fields: Dict[str, DataclassField] = cls._create_optional_field_map(item)
        partial_type: Type[T] = dataclass(  # pyright: ignore
            type(f"Partial{item.__name__}", (item,), {"__dataclass_fields__": fields})
        )
        annotated_ancestors = [a for a in getmro(partial_type) if hasattr(a, "__annotations__")]
        for ancestor in annotated_ancestors:
            for field_name, annotation in ancestor.__annotations__.items():
                if not isinstance(annotation, GenericAlias) or type(None) not in annotation.__args__:
                    partial_type.__annotations__[field_name] = Optional[annotation]
                else:
                    partial_type.__annotations__[field_name] = annotation

        cls._models[item] = partial_type

    @classmethod
    def _create_partial_typeddict(cls, item: Type[T]) -> None:
        """Receives a typeddict class and creates a new type with
        `total=False`.

        Args:
            item: A `TypedDict` class.
        """
        cls._models[item] = TypedDict(item.__name__, get_type_hints(item), total=False)  # type:ignore[operator]

    @staticmethod
    def _create_optional_field_map(item: "DataclassType") -> Dict[str, DataclassField]:
        """Creates a map of field name to optional dataclass Fields for a given
        dataclass.

        Args:
            item: A dataclass class.

        Returns:
            A map of field name to optional dataclass fields.
        """
        fields: Dict[str, DataclassField] = {}
        # https://github.com/python/typing/discussions/1056
        for field_name, dataclass_field in item.__dataclass_fields__.items():  # pyright:ignore
            if not isinstance(dataclass_field.type, GenericAlias) or type(None) not in dataclass_field.type.__args__:
                dataclass_field.type = Optional[dataclass_field.type]
            if dataclass_field.default_factory is MISSING:
                dataclass_field.default = None if dataclass_field.default is MISSING else dataclass_field.default
            fields[field_name] = dataclass_field
        return fields
