import os
from typing import Any, Dict, Generic, Optional, Tuple, TypeVar, cast

from pydantic import BaseModel, FilePath, create_model, validator
from typing_extensions import Type

try:
    # python 3.9 changed these variable
    from typing import _UnionGenericAlias as GenericAlias  # type: ignore
except ImportError:  # pragma: no cover
    from typing import _GenericAlias as GenericAlias  # type: ignore


T = TypeVar("T", bound=Type[BaseModel])


class Partial(Generic[T]):
    _models: Dict[T, Any] = {}

    def __class_getitem__(cls, item: T) -> T:
        """
        Modifies a given T subclass of BaseModel to be all optional
        """
        if not cls._models.get(item):
            field_definitions: Dict[str, Tuple[Any, None]] = {}
            for field_name, field_type in item.__annotations__.items():
                # we modify the field annotations to make it optional
                if not isinstance(field_type, GenericAlias) or type(None) not in field_type.__args__:
                    field_definitions[field_name] = (Optional[field_type], None)
                else:
                    field_definitions[field_name] = (field_type, None)
                cls._models[item] = create_model("Partial" + item.__name__, **field_definitions)
        return cast(T, cls._models.get(item))


class FileData(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    path: FilePath
    filename: str
    stat_result: Optional[os.stat_result] = None

    @validator("stat_result", always=True)
    def validate_status_code(  # pylint: disable=no-self-argument,no-self-use
        cls, _: Optional[tuple], values: Dict[str, Any]
    ) -> os.stat_result:
        """Set the stat_result value for the given filepath"""
        return os.stat(cast(str, values.get("path")))
