from typing import Dict, List, Optional, Union

from pydantic.v1 import BaseModel as BaseModelV1
from pydantic.v1.dataclasses import dataclass as dataclass_v1

from tests.models import DataclassPet


class PydanticV1Person(BaseModelV1):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    union: Union[int, List[str]]
    pets: Optional[List[DataclassPet]] = None


@dataclass_v1
class PydanticV1DataclassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    union: Union[int, List[str]]
    pets: Optional[List[DataclassPet]] = None
