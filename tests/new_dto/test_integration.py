from __future__ import annotations

from starlite import post
from starlite.status_codes import HTTP_201_CREATED
from starlite.testing import create_test_client

from . import ConcreteDTO, Model


def test_dto_data() -> None:
    @post(path="/")
    def post_handler(data: ConcreteDTO) -> ConcreteDTO:
        assert isinstance(data, ConcreteDTO)
        assert data.to_model() == Model(a=1, b="two")
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=b'{"a":1,"b":"two"}')
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == {"a": 1, "b": "two"}


def test_dto_iterable_data() -> None:
    @post(path="/")
    def post_handler(data: list[ConcreteDTO]) -> list[ConcreteDTO]:
        assert isinstance(data, list)
        for item in data:
            assert isinstance(item, ConcreteDTO)
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=b'[{"a":1,"b":"two"},{"a":3,"b":"four"}]')
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == [{"a": 1, "b": "two"}, {"a": 3, "b": "four"}]


def test_dto_supported_data() -> None:
    @post(path="/", data_dto=ConcreteDTO, return_dto=ConcreteDTO)
    def post_handler(data: Model) -> Model:
        assert isinstance(data, Model)
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=b'{"a":1,"b":"two"}')
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == {"a": 1, "b": "two"}


def test_dto_supported_iterable_data() -> None:
    @post(path="/", data_dto=ConcreteDTO, return_dto=ConcreteDTO)
    def post_handler(data: list[Model]) -> list[Model]:
        assert isinstance(data, list)
        for item in data:
            assert isinstance(item, Model)
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=b'[{"a":1,"b":"two"},{"a":3,"b":"four"}]')
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == [{"a": 1, "b": "two"}, {"a": 3, "b": "four"}]
