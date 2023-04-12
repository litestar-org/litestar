from dataclasses import dataclass as vanilla_dataclass
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

import attrs
import msgspec
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass as pydantic_dataclass
from typing_extensions import NotRequired, Required, TypedDict


class Species(str, Enum):
    DOG = "Dog"
    CAT = "Cat"
    MONKEY = "Monkey"
    PIG = "Pig"


class Pet(BaseModel):
    name: str
    species: Species = Field(default=Species.MONKEY)
    age: float


class Person(BaseModel):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[Pet]] = None


class PersonFactory(ModelFactory[Person]):
    __model__ = Person


class PetFactory(ModelFactory[Pet]):
    __model__ = Pet


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


class TypedDictPerson(TypedDict):
    first_name: Required[str]
    last_name: Required[str]
    id: Required[str]
    optional: NotRequired[Optional[str]]
    complex: Required[Dict[str, List[Dict[str, str]]]]
    pets: NotRequired[Optional[List[Pet]]]


@attrs.define
class AttrsPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[Pet]]


class MsgSpecStructPerson(msgspec.Struct):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[Pet]]


class User(BaseModel):
    name: str
    id: UUID


class UserFactory(ModelFactory[User]):
    __model__ = User
