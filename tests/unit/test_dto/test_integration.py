from __future__ import annotations

from typing import Dict
from unittest.mock import MagicMock

from litestar import Controller, Router, post
from litestar.testing import create_test_client

from . import Model, ModelDataDTO, ModelReturnDTO


def test_dto_defined_on_handler() -> None:
    @post(dto=ModelDataDTO, signature_namespace={"Model": Model})
    def handler(data: Model) -> Model:
        assert data == Model(a=1, b="2")
        return data

    with create_test_client(route_handlers=handler) as client:
        response = client.post("/", json={"what": "ever"})
        assert response.status_code == 201
        assert response.json() == {"a": 1, "b": "2"}


def test_dto_defined_on_controller() -> None:
    class MyController(Controller):
        dto = ModelDataDTO

        @post()
        def handler(self, data: Model) -> Model:
            assert data == Model(a=1, b="2")
            return data

    with create_test_client(route_handlers=MyController) as client:
        response = client.post("/", json={"what": "ever"})
        assert response.status_code == 201
        assert response.json() == {"a": 1, "b": "2"}


def test_dto_defined_on_router() -> None:
    @post()
    def handler(data: Model) -> Model:
        assert data == Model(a=1, b="2")
        return data

    router = Router(path="/", route_handlers=[handler], dto=ModelDataDTO)

    with create_test_client(route_handlers=router) as client:
        response = client.post("/", json={"what": "ever"})
        assert response.status_code == 201
        assert response.json() == {"a": 1, "b": "2"}


def test_dto_defined_on_app() -> None:
    @post()
    def handler(data: Model) -> Model:
        assert data == Model(a=1, b="2")
        return data

    with create_test_client(route_handlers=handler, dto=ModelDataDTO) as client:
        response = client.post("/", json={"what": "ever"})
        assert response.status_code == 201
        assert response.json() == {"a": 1, "b": "2"}


def test_set_dto_none_disables_inherited_dto() -> None:
    @post(dto=None, signature_namespace={"dict": Dict})
    def handler(data: dict[str, str]) -> dict[str, str]:
        assert data == {"hello": "world"}
        return data

    mock_dto = MagicMock(spec=ModelDataDTO)

    with create_test_client(route_handlers=handler, dto=mock_dto) as client:  # pyright:ignore
        response = client.post("/", json={"hello": "world"})
        assert response.status_code == 201
        assert response.json() == {"hello": "world"}
        mock_dto.assert_not_called()


def test_dto_and_return_dto() -> None:
    @post()
    def handler(data: Model) -> Model:
        assert data == Model(a=1, b="2")
        return data

    with create_test_client(route_handlers=handler, dto=ModelDataDTO, return_dto=ModelReturnDTO) as client:
        response = client.post("/", json={"what": "ever"})
        assert response.status_code == 201
        assert response.json() == {"a": 1, "b": "2"}
