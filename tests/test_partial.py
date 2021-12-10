from typing import Optional

from pydantic import UUID4, BaseModel

from starlite import Partial


class Person(BaseModel):
    first_name: str
    last_name: str
    id: UUID4
    optional: Optional[str]


def test_partial():
    partial = Partial[Person]
    assert partial
