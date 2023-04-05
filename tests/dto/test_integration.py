from __future__ import annotations

from typing import Any, Dict, List

import pytest

from starlite import Starlite, get, post
from starlite.dto.factory.exc import InvalidAnnotation
from starlite.dto.factory.stdlib.dataclass import DataclassDTO
from starlite.status_codes import HTTP_201_CREATED
from starlite.testing import create_test_client

from . import Model

ScalarDTO = DataclassDTO[Model]
IterableDTO = DataclassDTO[List[Model]]


def test_dto_data() -> None:
    @post(path="/")
    def post_handler(data: ScalarDTO) -> ScalarDTO:
        assert isinstance(data, DataclassDTO)
        assert data.data == Model(a=1, b="two")
        return data

    with create_test_client(route_handlers=[post_handler], debug=True) as client:
        post_response = client.post("/", content=b'{"a":1,"b":"two"}', headers={"content-type": "application/json"})
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == {"a": 1, "b": "two"}


def test_dto_iterable_data() -> None:
    @post(path="/")
    def post_handler(data: IterableDTO) -> IterableDTO:
        assert isinstance(data, DataclassDTO)
        assert isinstance(data.data, list)
        for item in data.data:
            assert isinstance(item, Model)
        return data

    with create_test_client(route_handlers=[post_handler]) as client:
        post_response = client.post(
            "/", content=b'[{"a":1,"b":"two"},{"a":3,"b":"four"}]', headers={"content-type": "application/json"}
        )
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == [{"a": 1, "b": "two"}, {"a": 3, "b": "four"}]


def test_dto_supported_data() -> None:
    @post(path="/", data_dto=DataclassDTO[Model], return_dto=DataclassDTO[Model])
    def post_handler(data: Model) -> Model:
        return data

    with create_test_client(
        route_handlers=[post_handler], debug=True, preferred_validation_backend="pydantic"
    ) as client:
        post_response = client.post("/", content=b'{"a":1,"b":"two"}', headers={"content-type": "application/json"})
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == {"a": 1, "b": "two"}


def test_dto_supported_iterable_data() -> None:
    @post(path="/", data_dto=DataclassDTO[List[Model]], return_dto=DataclassDTO[List[Model]])
    def post_handler(data: list[Model]) -> list[Model]:
        assert isinstance(data, list)
        for item in data:
            assert isinstance(item, Model)
        return data

    with create_test_client(route_handlers=[post_handler], signature_namespace={"list": List}) as client:
        post_response = client.post(
            "/", content=b'[{"a":1,"b":"two"},{"a":3,"b":"four"}]', headers={"content-type": "application/json"}
        )
        assert post_response.status_code == HTTP_201_CREATED
        assert post_response.json() == [{"a": 1, "b": "two"}, {"a": 3, "b": "four"}]


def test_exception_if_incompatible_data_dto_type() -> None:
    @post(path="/", data_dto=DataclassDTO[Model], signature_namespace={"dict": Dict})
    def post_handler(data: dict[str, Any]) -> None:
        ...

    with pytest.raises(InvalidAnnotation):
        Starlite(route_handlers=[post_handler])


def test_exception_if_incompatible_return_dto_type() -> None:
    @get(return_dto=DataclassDTO[List[Model]], signature_namespace={"list": List})
    def get_handler() -> list[int]:
        return []

    with pytest.raises(InvalidAnnotation):
        Starlite(route_handlers=[get_handler])
