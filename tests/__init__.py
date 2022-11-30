from dataclasses import dataclass as vanilla_dataclass
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

import msgspec
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic_factories import ModelFactory
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import INTEGER, JSONB, TEXT
from sqlalchemy.orm import declarative_base
from typing_extensions import TypedDict

Base = declarative_base()


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


class Car(Base):  # pyright: ignore
    __tablename__ = "db_cars"

    id = Column(INTEGER, primary_key=True)
    year = Column(INTEGER)
    make = Column(TEXT)
    model = Column(TEXT)
    horsepower = Column(INTEGER)
    color_codes = Column(JSONB)


class User(BaseModel):
    name: str
    id: UUID


class UserFactory(ModelFactory[User]):
    __model__ = User
