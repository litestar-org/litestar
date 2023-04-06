from __future__ import annotations

import pytest

from starlite import post
from starlite.testing import create_test_client
from tests.dto import MockDTO, Model


@pytest.mark.xfail
def test_dto_defined_on_handler() -> None:
    @post(dto=MockDTO)
    def handler(data: Model) -> Model:
        assert data == Model(a=1, b="2")
        return data

    with create_test_client(route_handlers=handler, preferred_validation_backend="attrs") as client:
        response = client.post("/", json={"what": "ever"})
        assert response.status_code == 201
        assert response.json() == {"a": 1, "b": "2"}
