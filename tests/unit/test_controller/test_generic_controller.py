from __future__ import annotations

from dataclasses import asdict
from typing import Any

from litestar import Request
from litestar.controller.generic_mixins import SyncCreateMixin
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client
from tests import VanillaDataClassPerson, VanillaDataClassPersonFactory


def test_generic_controller() -> None:
    class GenericPersonController(SyncCreateMixin[VanillaDataClassPerson]):
        model_type = VanillaDataClassPerson
        path = "/"

        def perform_create(self, data: dict[str, Any], request: Request[Any, Any, Any]) -> VanillaDataClassPerson:
            return VanillaDataClassPersonFactory.build(**data)

    with create_test_client(GenericPersonController) as client:
        response = client.post("/", json=asdict(VanillaDataClassPersonFactory.build(pets=None)))
        assert response.status_code == HTTP_201_CREATED
        assert response.json()
