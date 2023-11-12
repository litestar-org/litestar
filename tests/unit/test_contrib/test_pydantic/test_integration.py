from typing import Any, Dict, List, Type, Union

import pydantic as pydantic_v2
import pytest
from pydantic import v1 as pydantic_v1
from typing_extensions import Annotated

from litestar import post
from litestar.contrib.pydantic.pydantic_dto_factory import PydanticDTO
from litestar.enums import RequestEncodingType
from litestar.params import Body, Parameter
from litestar.status_codes import HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client
from tests.unit.test_contrib.test_pydantic.models import PydanticPerson, PydanticV1Person

from . import PydanticVersion


@pytest.mark.parametrize(("meta",), [(None,), (Body(media_type=RequestEncodingType.URL_ENCODED),)])
def test_pydantic_v1_validation_error_raises_400(meta: Any) -> None:
    class Model(pydantic_v1.BaseModel):
        foo: str = pydantic_v1.Field(max_length=2)

    ModelDTO = PydanticDTO[Model]

    annotation: Any
    annotation = Annotated[Model, meta] if meta is not None else Model

    @post(dto=ModelDTO, signature_namespace={"annotation": annotation})
    def handler(data: annotation) -> Any:  # pyright: ignore
        return data

    model_json = {"foo": "too long"}
    expected_errors: List[Dict[str, Any]]

    expected_errors = [
        {
            "loc": ["foo"],
            "msg": "ensure this value has at most 2 characters",
            "type": "value_error.any_str.max_length",
            "ctx": {"limit_value": 2},
        }
    ]

    with create_test_client(route_handlers=handler) as client:
        kws = {"data": model_json} if meta else {"json": model_json}
        response = client.post("/", **kws)  # type: ignore[arg-type]
        extra = response.json()["extra"]

        assert response.status_code == 400
        assert extra == expected_errors


@pytest.mark.parametrize(("meta",), [(None,), (Body(media_type=RequestEncodingType.URL_ENCODED),)])
def test_pydantic_v2_validation_error_raises_400(meta: Any) -> None:
    class Model(pydantic_v2.BaseModel):
        foo: str = pydantic_v2.Field(max_length=2)

    ModelDTO = PydanticDTO[Model]

    annotation: Any
    annotation = Annotated[Model, meta] if meta is not None else Model

    @post(dto=ModelDTO, signature_namespace={"annotation": annotation})
    def handler(data: annotation) -> Any:  # pyright: ignore
        return data

    model_json = {"foo": "too long"}
    expected_errors: List[Dict[str, Any]]

    expected_errors = [
        {
            "type": "string_too_long",
            "loc": ["foo"],
            "msg": "String should have at most 2 characters",
            "input": "too long",
            "ctx": {"max_length": 2},
        }
    ]

    with create_test_client(route_handlers=handler) as client:
        kws = {"data": model_json} if meta else {"json": model_json}
        response = client.post("/", **kws)  # type: ignore[arg-type]

        extra = response.json()["extra"]
        extra[0].pop("url")

        assert response.status_code == 400
        assert extra == expected_errors


def test_default_error_handling() -> None:
    @post("/{param:int}")
    def my_route_handler(param: int, data: PydanticPerson) -> None:
        ...

    with create_test_client(my_route_handler) as client:
        response = client.post("/123", json={"first_name": "moishe"})
        extra = response.json().get("extra")
        assert extra is not None
        assert len(extra) == 4


def test_default_error_handling_v1() -> None:
    @post("/{param:int}")
    def my_route_handler(param: int, data: PydanticV1Person) -> None:
        ...

    with create_test_client(my_route_handler) as client:
        response = client.post("/123", json={"first_name": "moishe"})
        extra = response.json().get("extra")
        assert extra is not None
        assert len(extra) == 3


def test_signature_model_invalid_input(
    base_model: Type[Union[pydantic_v2.BaseModel, pydantic_v1.BaseModel]], pydantic_version: PydanticVersion
) -> None:
    class OtherChild(base_model):  # type: ignore[misc, valid-type]
        val: List[int]

    class Child(base_model):  # type: ignore[misc, valid-type]
        val: int
        other_val: int

    class Parent(base_model):  # type: ignore[misc, valid-type]
        child: Child
        other_child: OtherChild

    @post("/")
    def test(
        data: Parent,
        int_param: int,
        length_param: str = Parameter(min_length=2),
        int_header: int = Parameter(header="X-SOME-INT"),
        int_cookie: int = Parameter(cookie="int-cookie"),
    ) -> None:
        ...

    with create_test_client(route_handlers=[test], signature_types=[Parent]) as client:
        client.cookies.update({"int-cookie": "cookie"})
        response = client.post(
            "/",
            json={"child": {"val": "a", "other_val": "b"}, "other_child": {"val": [1, "c"]}},
            params={"int_param": "param", "length_param": "d"},
            headers={"X-SOME-INT": "header"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        data = response.json()

        assert data
        if pydantic_version == "v1":
            assert data["extra"] == [
                {"key": "child.val", "message": "value is not a valid integer"},
                {"key": "child.other_val", "message": "value is not a valid integer"},
                {"key": "other_child.val.1", "message": "value is not a valid integer"},
            ]
        else:
            assert data["extra"] == [
                {
                    "message": "Input should be a valid integer, unable to parse string as an integer",
                    "key": "child.val",
                },
                {
                    "message": "Input should be a valid integer, unable to parse string as an integer",
                    "key": "child.other_val",
                },
                {
                    "message": "Input should be a valid integer, unable to parse string as an integer",
                    "key": "other_child.val.1",
                },
            ]
