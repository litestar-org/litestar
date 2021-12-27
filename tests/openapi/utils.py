from datetime import date, datetime
from enum import Enum
from typing import Any, List, Optional, Union

from openapi_schema_pydantic import Example
from pydantic import conbytes, condecimal, confloat, conint, conlist, conset, constr

from starlite import (
    Controller,
    HTTPException,
    MediaType,
    Parameter,
    Partial,
    delete,
    get,
    patch,
    post,
    put,
)
from starlite.config import SchemaGenerationConfig
from starlite.types import ResponseHeader
from tests import Person, Pet, VanillaDataClassPerson

default_config = SchemaGenerationConfig()


class PetException(HTTPException):
    status_code = 406


class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    ANY = "A"


class PersonController(Controller):
    path = "/{service_id:int}/person"

    @get()
    def get_persons(
        self,
        # expected to be ignored
        headers: Any,
        request: Any,
        # required query parameters below
        page: int,
        name: Optional[Union[str, List[str]]],  # intentionally without default
        page_size: int = Parameter(
            query="pageSize",
            description="Page Size Description",
            title="Page Size Title",
            examples=[Example(description="example value", value=1)],
        ),
        # path parameter
        service_id: int = conint(gt=0),
        # non-required query parameters below
        from_date: Optional[Union[int, datetime, date]] = None,
        to_date: Optional[Union[int, datetime, date]] = None,
        gender: Optional[Union[Gender, List[Gender]]] = Parameter(
            examples=[Example(value="M"), Example(value=["M", "O"])]
        ),
        # header parameter
        secret_header: str = Parameter(header="secret"),
        # cookie parameter
        cookie_value: int = Parameter(cookie="value"),
    ) -> List[Person]:
        pass

    @post()
    def create_person(
        self, data: Person, secret_header: str = Parameter(header="secret"), media_type=MediaType.TEXT
    ) -> Person:
        pass

    @post(path="/bulk")
    def bulk_create_person(self, data: List[Person], secret_header: str = Parameter(header="secret")) -> List[Person]:
        pass

    @put(path="/bulk")
    def bulk_update_person(self, data: List[Person], secret_header: str = Parameter(header="secret")) -> List[Person]:
        pass

    @patch(path="/bulk")
    def bulk_partial_update_person(
        self, data: List[Partial[Person]], secret_header: str = Parameter(header="secret")
    ) -> List[Person]:
        pass

    @get(path="/{person_id:str}")
    def get_person_by_id(self, person_id: str) -> Person:
        pass

    @patch(path="/{person_id:str}")
    def partial_update_person(self, person_id: str, data: Partial[Person]) -> Person:
        pass

    @put(path="/{person_id:str}")
    def update_person(self, person_id: str, data: Person) -> Person:
        pass

    @delete(path="/{person_id:str}")
    def delete_person(self, person_id: str) -> None:
        pass

    @get(path="/dataclass")
    def get_person_dataclass(self) -> VanillaDataClassPerson:
        pass


class PetController(Controller):
    path = "/pet"

    @get()
    def pets(self) -> List[Pet]:
        pass

    @get(path="/owner-or-pet", response_headers={"x-my-tag": ResponseHeader(value="123")}, raises=[PetException])
    def get_pets_or_owners(self) -> List[Union[Person, Pet]]:
        pass


constrained_numbers = [
    conint(gt=10, lt=100),
    conint(ge=10, le=100),
    conint(ge=10, le=100, multiple_of=7),
    confloat(gt=10, lt=100),
    confloat(ge=10, le=100),
    confloat(ge=10, le=100, multiple_of=4.2),
    confloat(gt=10, lt=100, multiple_of=10),
    condecimal(gt=10, lt=100),
    condecimal(ge=10, le=100),
    condecimal(gt=10, lt=100, multiple_of=5),
    condecimal(ge=10, le=100, multiple_of=2),
]
constrained_string = [
    constr(regex="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=1, regex="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=10, regex="^[a-zA-Z]$"),
    constr(to_lower=True, min_length=10, max_length=100, regex="^[a-zA-Z]$"),
    constr(min_length=1),
    constr(min_length=10),
    constr(min_length=10, max_length=100),
    conbytes(to_lower=True, min_length=1),
    conbytes(to_lower=True, min_length=10),
    conbytes(to_lower=True, min_length=10, max_length=100),
    conbytes(min_length=1),
    conbytes(min_length=10),
    conbytes(min_length=10, max_length=100),
]
constrained_collection = [
    conlist(int, min_items=1),
    conlist(int, min_items=1, max_items=10),
    conset(int, min_items=1),
    conset(int, min_items=1, max_items=10),
]
