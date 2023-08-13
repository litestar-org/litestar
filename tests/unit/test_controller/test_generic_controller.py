from __future__ import annotations

from dataclasses import asdict

from litestar import get, post
from litestar.controller import GenericController
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from litestar.testing import create_test_client
from tests import VanillaDataClassPerson, VanillaDataClassPersonFactory


def test_generic_controller() -> None:
    class GenericPersonController(GenericController[VanillaDataClassPerson]):
        model_type = VanillaDataClassPerson
        path = "/"

        @get("/{id:int}")
        def get_handler(self, id: int) -> VanillaDataClassPerson:
            return VanillaDataClassPersonFactory.build(id=id)

        @post("/")
        def post_handler(self, data: VanillaDataClassPerson) -> VanillaDataClassPerson:
            return VanillaDataClassPersonFactory.build(**asdict(data))

        @get("/")
        def get_collection_handler(self) -> list[VanillaDataClassPerson]:
            return VanillaDataClassPersonFactory.batch(5)

    with create_test_client(GenericPersonController) as client:
        response = client.get("/1")
        assert response.status_code == HTTP_200_OK
        assert response.json()

        response = client.post("/", json=asdict(VanillaDataClassPersonFactory.build()))
        assert response.status_code == HTTP_201_CREATED
        assert response.json()

        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert len(response.json()) == 5
