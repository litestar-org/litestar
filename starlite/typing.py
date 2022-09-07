import dataclasses
from dataclasses import _MISSING_TYPE
from dataclasses import Field as DataclassField
from dataclasses import is_dataclass
from typing import (
    Any,
    Dict,
    Generic,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)

from pydantic import BaseModel, create_model
from pydantic_factories.protocols import DataclassProtocol

from starlite.exceptions import ImproperlyConfiguredException
from starlite.utils import is_class_and_subclass

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore

T = TypeVar("T", bound=Union[BaseModel, DataclassProtocol])


class Partial(Generic[T]):
    """Partial is a special typing helper that takes a generic T, which must be
    a subclass of pydantic's BaseModel.

    and returns to static type checkers a version of this T in which all fields - and nested fields - are optional.
    """

    _models: Dict[Type[T], Any] = {}

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        """Modifies a given T subclass of BaseModel to be all optional."""
        if not is_class_and_subclass(item, BaseModel) and not is_dataclass(item):
            raise ImproperlyConfiguredException("Unsupported value type passed as the generic argument T to Partial[T]")
        if not cls._models.get(item):
            if issubclass(item, BaseModel):
                cls._create_partial_pydantic_model(item=item)
            else:
                cls._create_partial_dataclass(item=item)
        return cast("Type[T]", cls._models.get(item))

    @classmethod
    def _create_partial_pydantic_model(cls, item: Type[BaseModel]) -> None:
        field_definitions: Dict[str, Tuple[Any, None]] = {}
        for field_name, field_type in get_type_hints(item).items():
            # we modify the field annotations to make it optional
            if not isinstance(field_type, GenericAlias) or type(None) not in field_type.__args__:
                field_definitions[field_name] = (Optional[field_type], None)
            else:
                field_definitions[field_name] = (field_type, None)
        cls._models[item] = create_model(f"Partial{item.__name__}", **field_definitions)  # type: ignore

    @classmethod
    def _create_partial_dataclass(cls, item: Type[DataclassProtocol]) -> None:
        fields: Dict[str, DataclassField] = {}
        for field_name, dataclass_field in item.__dataclass_fields__.items():
            if not isinstance(dataclass_field.type, GenericAlias) or type(None) not in dataclass_field.type.__args__:
                dataclass_field.type = Optional[dataclass_field.type]
            if type(dataclass_field.default_factory) is _MISSING_TYPE:
                dataclass_field.default = (
                    None if type(dataclass_field.default) is _MISSING_TYPE else dataclass_field.default
                )
            dataclass_field.kw_only = True
            fields[field_name] = dataclass_field
        partial_type = dataclasses.dataclass(type(f"Partial{item.__name__}", (item,), {"__dataclass_fields__": fields}))
        for field_name, annotation in item.__annotations__.items():
            if not isinstance(annotation, GenericAlias) or type(None) not in annotation.__args__:
                partial_type.__annotations__[field_name] = Optional[annotation]
            else:
                partial_type.__annotations__[field_name] = annotation
        cls._models[item] = partial_type
