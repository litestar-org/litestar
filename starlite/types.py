from typing import Any, Dict, Generic, Optional, Tuple, TypeVar, cast

from pydantic import BaseModel, create_model
from typing_extensions import Type

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore


T = TypeVar("T", bound=Type[BaseModel])


class Partial(Generic[T]):
    def __class_getitem__(cls, item: T) -> T:
        """
        Modifies a given T subclass of BaseModel to be all optional
        """
        field_definitions: Dict[str, Tuple[Any, None]] = {}
        for field_name, field_type in item.__annotations__.items():
            # we modify the field annotations to make it optional
            if not isinstance(field_type, GenericAlias) or type(None) not in field_type.__args__:
                field_definitions[field_name] = (Optional[field_type], None)
            else:
                field_definitions[field_name] = (field_type, None)
        return cast(T, create_model("Partial" + item.__name__, **field_definitions))
