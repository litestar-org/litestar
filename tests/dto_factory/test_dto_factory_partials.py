from starlite.dto import DTOFactory
from starlite.partial import Partial
from tests import Person

dto_factory = DTOFactory()


def test_partial_dto_pydantic() -> None:
    dto_partial_person = Partial[Person]
    bob = dto_partial_person(first_name="Bob")  # type: ignore
    assert bob.first_name == "Bob"  # type: ignore
