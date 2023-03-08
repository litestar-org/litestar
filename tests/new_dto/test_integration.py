from __future__ import annotations

from typing import List

from starlite import post
from starlite.status_codes import HTTP_201_CREATED
from starlite.testing import create_test_client

from . import ConcreteDTO, Model

ScalarDTO = ConcreteDTO[Model]
IterableDTO = ConcreteDTO[List[Model]]


def test_dto_data() -> None:
    @post(path="/")
    def post_handler(data: ScalarDTO) -> ScalarDTO:
        assert isinstance(data, ConcreteDTO)
        assert data.data == Model(a=1, b="two")
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=b'{"a":1,"b":"two"}')
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == {"a": 1, "b": "two"}


def test_dto_iterable_data() -> None:
    @post(path="/")
    def post_handler(data: IterableDTO) -> IterableDTO:
        assert isinstance(data, ConcreteDTO)
        assert isinstance(data.data, list)
        for item in data.data:
            assert isinstance(item, Model)
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=b'[{"a":1,"b":"two"},{"a":3,"b":"four"}]')
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == [{"a": 1, "b": "two"}, {"a": 3, "b": "four"}]


def test_dto_supported_data() -> None:
    @post(path="/", data_dto=ConcreteDTO[Model], return_dto=ConcreteDTO[Model])
    def post_handler(data: Model) -> Model:
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=b'{"a":1,"b":"two"}')
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == {"a": 1, "b": "two"}


def test_dto_supported_iterable_data() -> None:
    @post(path="/", data_dto=ConcreteDTO[List[Model]], return_dto=ConcreteDTO[List[Model]])
    def post_handler(data: list[Model]) -> list[Model]:
        assert isinstance(data, list)
        for item in data:
            assert isinstance(item, Model)
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post("/", content=b'[{"a":1,"b":"two"},{"a":3,"b":"four"}]')
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == [{"a": 1, "b": "two"}, {"a": 3, "b": "four"}]
