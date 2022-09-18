from pathlib import PurePath, PurePosixPath
from typing import Any

from pydantic import BaseModel, SecretStr


def default_serializer(value: Any) -> Any:
    """
    Args:
        value: A value to serialize
    Returns:
        A serialized value
    Raises:
        TypeError: if value is not supported
    """
    if isinstance(value, BaseModel):
        return value.dict()
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, (PurePath, PurePosixPath)):
        return str(value)
    raise TypeError("unsupported type")
