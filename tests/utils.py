from dataclasses import dataclass as vanilla_dataclass
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic_factories import ModelFactory


class Species(str, Enum):
    DOG = "Dog"
    CAT = "Cat"
    MONKEY = "Monkey"
    PIG = "Pig"


class Pet(BaseModel):
    name: str
    species: Species
    age: float


class Person(BaseModel):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[Pet]] = None


class PersonFactory(ModelFactory):
    __model__ = Person


@vanilla_dataclass
class VanillaDataClassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[Pet]] = None


@pydantic_dataclass
class PydanticDataClassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[Pet]] = None


class ResponseHeaders(BaseModel):
    application_type: str = "APP"
    Access_Control_Allow_Origin: str = "*"
    x_my_tag: str
    omitted_tag: Optional[str] = None
