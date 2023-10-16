import dataclasses
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

import attrs
import msgspec
from polyfactory.factories import DataclassFactory
from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass
from typing_extensions import NotRequired, Required, TypedDict


class Species(str, Enum):
    DOG = "Dog"
    CAT = "Cat"
    MONKEY = "Monkey"
    PIG = "Pig"


@dataclasses.dataclass
class DataclassPet:
    name: str
    age: float
    species: Species = Species.MONKEY


@dataclasses.dataclass
class DataclassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[DataclassPet]] = None


@pydantic_dataclass
class PydanticDataclassPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[DataclassPet]] = None


class TypedDictPerson(TypedDict):
    first_name: Required[str]
    last_name: Required[str]
    id: Required[str]
    optional: NotRequired[Optional[str]]
    complex: Required[Dict[str, List[Dict[str, str]]]]
    pets: NotRequired[Optional[List[DataclassPet]]]


class PydanticPerson(BaseModel):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[DataclassPet]] = None


@attrs.define
class AttrsPerson:
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[DataclassPet]]


class MsgSpecStructPerson(msgspec.Struct):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]
    pets: Optional[List[DataclassPet]]


@dataclasses.dataclass
class User:
    name: str
    id: UUID


class UserFactory(DataclassFactory[User]):
    __model__ = User


class DataclassPersonFactory(DataclassFactory[DataclassPerson]):
    __model__ = DataclassPerson


class DataclassPetFactory(DataclassFactory[DataclassPet]):
    __model__ = DataclassPet
