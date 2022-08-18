from typing import (
    Any,
    Dict,
    Generic,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
    get_type_hints,
)

from pydantic import BaseModel, create_model

from starlite.exceptions import ImproperlyConfiguredException
from starlite.utils import is_class_and_subclass

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore

T = TypeVar("T", bound=BaseModel)


class Partial(Generic[T]):
    """Partial is a special typing helper that takes a generic T, which must be
    a subclass of pydantic's BaseModel.

    and returns to static type checkers a version of this T in which all fields - and nested fields - are optional.
    """

    _models: Dict[Type[T], Any] = {}

    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        """Modifies a given T subclass of BaseModel to be all optional."""
        if not is_class_and_subclass(item, BaseModel):
            raise ImproperlyConfiguredException(f"Partial[{item}] must be a subclass of BaseModel")
        if not cls._models.get(item):
            field_definitions: Dict[str, Tuple[Any, None]] = {}
            # traverse the object's mro and get all annotations
            # until we find a BaseModel.
            for obj in item.mro():
                if issubclass(obj, BaseModel):
                    for field_name, field_type in get_type_hints(obj).items():
                        # we modify the field annotations to make it optional
                        if not isinstance(field_type, GenericAlias) or type(None) not in field_type.__args__:
                            field_definitions[field_name] = (Optional[field_type], None)
                        else:
                            field_definitions[field_name] = (field_type, None)
                else:
                    break
            cls._models[item] = create_model(f"Partial{item.__name__}", **field_definitions)  # type: ignore
        return cast("Type[T]", cls._models.get(item))
