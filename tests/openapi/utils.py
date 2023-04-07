from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import (
    conbytes,
    condate,
    condecimal,
    confloat,
    conint,
    conlist,
    conset,
    constr,
)

from litestar import Controller, MediaType, delete, get, patch, post, put
from litestar.datastructures import ResponseHeader, State
from litestar.exceptions import HTTPException
from litestar.openapi.spec.example import Example
from litestar.params import Parameter
from litestar.partial import Partial
from tests import Person, PersonFactory, Pet, VanillaDataClassPerson


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
        state: State,
        query: Dict[str, Any],
        cookies: Dict[str, Any],
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
        service_id: int = conint(gt=0),  # type: ignore
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
        return []

    @post(media_type=MediaType.TEXT)
    def create_person(self, data: Person, secret_header: str = Parameter(header="secret")) -> Person:
        return data

    @post(path="/bulk")
    def bulk_create_person(self, data: List[Person], secret_header: str = Parameter(header="secret")) -> List[Person]:
        return []

    @put(path="/bulk")
    def bulk_update_person(self, data: List[Person], secret_header: str = Parameter(header="secret")) -> List[Person]:
        return []

    @patch(path="/bulk")
    def bulk_partial_update_person(
        self, data: List[Partial[Person]], secret_header: str = Parameter(header="secret")
    ) -> List[Person]:
        return []

    @get(path="/{person_id:str}")
    def get_person_by_id(self, person_id: str) -> Person:
        """Description in docstring."""
        return PersonFactory.build(id=person_id)

    @patch(path="/{person_id:str}", description="Description in decorator")
    def partial_update_person(self, person_id: str, data: Partial[Person]) -> Person:
        """Description in docstring."""
        return PersonFactory.build(id=person_id)

    @put(path="/{person_id:str}")
    def update_person(self, person_id: str, data: Person) -> Person:
        """Multiline docstring example.

        Line 3.
        """
        return data

    @delete(path="/{person_id:str}")
    def delete_person(self, person_id: str) -> None:
        return None

    @get(path="/dataclass")
    def get_person_dataclass(self) -> VanillaDataClassPerson:
        return VanillaDataClassPerson(
            first_name="Moishe", last_name="zuchmir", id="1", optional=None, complex={}, pets=None
        )


class PetController(Controller):
    path = "/pet"

    @get()
    def pets(self) -> List[Pet]:
        return []

    @get(path="/owner-or-pet", response_headers=[ResponseHeader(name="x-my-tag", value="123")], raises=[PetException])
    def get_pets_or_owners(self) -> List[Union[Person, Pet]]:
        return []


constrained_numbers = [
    conint(gt=10, lt=100),
    conint(ge=10, le=100),
    conint(ge=10, le=100, multiple_of=7),
    confloat(gt=10, lt=100),
    confloat(ge=10, le=100),
    confloat(ge=10, le=100, multiple_of=4.2),
    confloat(gt=10, lt=100, multiple_of=10),
    condecimal(gt=Decimal("10"), lt=Decimal("100")),
    condecimal(ge=Decimal("10"), le=Decimal("100")),
    condecimal(gt=Decimal("10"), lt=Decimal("100"), multiple_of=Decimal("5")),
    condecimal(ge=Decimal("10"), le=Decimal("100"), multiple_of=Decimal("2")),
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
constrained_dates = [
    condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
    condate(gt=date.today() - timedelta(days=10), lt=date.today() + timedelta(days=100)),
    condate(ge=date.today() - timedelta(days=10), le=date.today() + timedelta(days=100)),
]
