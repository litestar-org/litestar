from dataclasses import dataclass as vanilla_dataclass
from typing import Dict, List, Optional

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic_factories import ModelFactory


class Person(BaseModel):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]


class PersonFactory(ModelFactory):
    __model__ = Person


@vanilla_dataclass
class VanillaDataClassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]


@pydantic_dataclass
class PydanticDataClassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
