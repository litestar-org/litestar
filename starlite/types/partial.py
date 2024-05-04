from dataclasses import make_dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
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
    is_dataclass_class,
    is_typed_dict,
)

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore

if TYPE_CHECKING:
    from typing import Union  # noqa: F401  # nopycln: import  # pyright: ignore

    from typing_extensions import TypeAlias

    from starlite.types.builtin_types import DataclassClass, TypedDictClass

T = TypeVar("T")

SupportedTypes: "TypeAlias" = "Union[DataclassClass, Type[BaseModel], TypedDictClass]"
"""Types that are supported by :class:`Partial <starlite.types.partial.Partial>`"""


class Partial(Generic[T]):
    """Type generation for PATCH routes.

    Partial is a special typing helper that takes a generic T, which must be a
    :class:`TypedDict <typing.TypedDict>`, dataclass or pydantic model class, and
    returns to static type checkers a version of this T in which all fields -
    and nested fields - are optional.
    """

    _models: Dict[SupportedTypes, SupportedTypes] = {}  # pyright: ignore

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        """Take a pydantic model class, :class:`TypedDict <typing.TypedDict>` or a dataclass and return an all optional
        version of that class.

        Args:
            item: A pydantic model, :class:`TypedDict <typing.TypedDict>` or dataclass class.

        Returns:
            A pydantic model, :class:`TypedDict <typing.TypedDict>`, or dataclass.
        """
        if item not in cls._models:
            if is_class_and_subclass(item, BaseModel):
                cls._create_partial_pydantic_model(item=item)
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
        field_definitions: List[Tuple[str, Type, Any]] = []
        for field_name, field_type in get_type_hints(item).items():
            if is_classvar(field_type):
                continue
            if not isinstance(field_type, GenericAlias) or NoneType not in field_type.__args__:
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
        type_hints: Dict[str, Any] = {}
        for key_name, value_type in get_type_hints(item).items():
            if NoneType in get_args(value_type):
                type_hints[key_name] = value_type
                continue
            type_hints[key_name] = Optional[value_type]
        type_name = cls._create_partial_type_name(item)
        cls._models[item] = TypedDict(type_name, type_hints, total=False)  # type:ignore

    @staticmethod
    def _create_partial_type_name(item: SupportedTypes) -> str:  # pyright: ignore
        return f"Partial{item.__name__}"
