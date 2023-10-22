from typing import Dict, List, Optional

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from tests.models import DataclassPet


@pydantic_dataclass
class PydanticDataclassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[DataclassPet]] = None


class PydanticPerson(BaseModel):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[DataclassPet]] = None
