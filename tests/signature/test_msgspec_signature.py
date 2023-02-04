from typing import List

from msgspec import to_builtins

from starlite import post
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client
from tests import PersonFactory, PersonStruct, PetFactory, PetStruct


def test_signature_with_msgpsec_types() -> None:
    pets = PetFactory.batch(2)

    @post("/pets")
    def pets_handler(data: PersonStruct) -> List[PetStruct]:
        return data.pets or []

    with create_test_client(pets_handler) as client:
        response = client.post("/pets", json=to_builtins(PersonStruct(**PersonFactory.build(pets=pets).dict())))
        assert response.status_code == HTTP_200_OK
        assert response.json() == [p.dict() for p in pets]
