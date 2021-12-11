from copy import deepcopy
from typing import Generic, Optional, Type, TypeVar

from pydantic import BaseModel
from pydantic.fields import ModelField

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore


T = TypeVar("T", bound=Type[BaseModel])


def set_field_optional(field: ModelField) -> ModelField:
    """Given a model field, set it to optional and update all sub_fields recursively"""
    field.required = False
    field.allow_none = True
    if field.sub_fields:
        for index, sub_field in enumerate(field.sub_fields):
            field.sub_fields[index] = set_field_optional(field=sub_field)
    return field


class Partial(Generic[T]):
    def __class_getitem__(cls, item: T) -> T:
        """
        Modifies a given T subclass of BaseModel to be all optional
        """
        item_copy = deepcopy(item)
        for field_name, field_type in item_copy.__annotations__.items():
            # we modify the field annotations to make it optional
            if not isinstance(field_type, GenericAlias) or type(None) not in field_type.__args__:
                item_copy.__annotations__[field_name] = Optional[field_type]
        for field_name, field in item_copy.__fields__.items():
            setattr(item_copy, field_name, set_field_optional(field))
        return item_copy
