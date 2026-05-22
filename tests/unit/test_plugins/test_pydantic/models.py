from typing import Optional, Union

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from tests.models import DataclassPet


@pydantic_dataclass
class PydanticDataclassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: dict[str, list[dict[str, str]]]
    union: Union[int, list[str]]
    pets: Optional[list[DataclassPet]] = None


class PydanticPerson(BaseModel):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: dict[str, list[dict[str, str]]]
    union: Union[int, list[str]]
    pets: Optional[list[DataclassPet]] = None
