from datetime import date, datetime
from typing import Any, Dict, List, Optional, Type, Union

import pytest
from pydantic import (
    conint,
)

from litestar import Controller, MediaType, delete, get, patch, post, put
from litestar.datastructures import ResponseHeader, State
from litestar.dto import DTOData
from litestar.openapi.spec.example import Example
from litestar.params import Parameter
from tests import PartialPersonDTO, PydanticPerson, PydanticPersonFactory, PydanticPet, VanillaDataClassPerson

from .utils import Gender, PetException


def create_person_controller() -> Type[Controller]:
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
        ) -> List[PydanticPerson]:
            return []

        @post(media_type=MediaType.TEXT)
        def create_person(
            self, data: PydanticPerson, secret_header: str = Parameter(header="secret")
        ) -> PydanticPerson:
            return data

        @post(path="/bulk", dto=PartialPersonDTO)
        def bulk_create_person(
            self, data: List[DTOData[PydanticPerson]], secret_header: str = Parameter(header="secret")
        ) -> List[PydanticPerson]:
            return []

        @put(path="/bulk")
        def bulk_update_person(
            self, data: List[PydanticPerson], secret_header: str = Parameter(header="secret")
        ) -> List[PydanticPerson]:
            return []

        @patch(path="/bulk", dto=PartialPersonDTO)
        def bulk_partial_update_person(
            self, data: List[DTOData[PydanticPerson]], secret_header: str = Parameter(header="secret")
        ) -> List[PydanticPerson]:
            return []

        @get(path="/{person_id:str}")
        def get_person_by_id(self, person_id: str) -> PydanticPerson:
            """Description in docstring."""
            return PydanticPersonFactory.build(id=person_id)

        @patch(path="/{person_id:str}", description="Description in decorator", dto=PartialPersonDTO)
        def partial_update_person(self, person_id: str, data: DTOData[PydanticPerson]) -> PydanticPerson:
            """Description in docstring."""
            return PydanticPersonFactory.build(id=person_id)

        @put(path="/{person_id:str}")
        def update_person(self, person_id: str, data: PydanticPerson) -> PydanticPerson:
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

    return PersonController


def create_pet_controller() -> Type[Controller]:
    class PetController(Controller):
        path = "/pet"

        @get()
        def pets(self) -> List[PydanticPet]:
            return []

        @get(
            path="/owner-or-pet", response_headers=[ResponseHeader(name="x-my-tag", value="123")], raises=[PetException]
        )
        def get_pets_or_owners(self) -> List[Union[PydanticPerson, PydanticPet]]:
            return []

    return PetController


@pytest.fixture
@pytest.mark.usefixtures("disable_warn_implicit_sync_to_thread")
def person_controller() -> Type[Controller]:
    return create_person_controller()


@pytest.fixture
@pytest.mark.usefixtures("disable_warn_implicit_sync_to_thread")
def pet_controller() -> Type[Controller]:
    return create_pet_controller()
