from typing import Dict, List, Optional

from pydantic import BaseModel
from pydantic_factories import ModelFactory


class Person(BaseModel):
    first_name: str
    last_name: str
    id: str
    optional: Optional[str]
    complex: Dict[str, List[Dict[str, str]]]


class PersonFactory(ModelFactory):
    __model__ = Person
