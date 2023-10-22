from typing import Any, Dict, List

from pydantic import VERSION, BaseModel, Field

from litestar import post
from litestar.contrib.pydantic.pydantic_dto_factory import PydanticDTO
from litestar.params import Parameter
from litestar.status_codes import HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client
from tests.unit.test_contrib.test_pydantic.models import PydanticPerson


def test_pydantic_validation_error_raises_400() -> None:
    class Model(BaseModel):
        foo: str = Field(max_length=2)

    ModelDTO = PydanticDTO[Model]

    @post(dto=ModelDTO, signature_types=[Model])
    def handler(data: Model) -> Model:
        return data

    model_json = {"foo": "too long"}
    expected_errors: List[Dict[str, Any]]

    if VERSION.startswith("1"):
        expected_errors = [
            {
                "loc": ["foo"],
                "msg": "ensure this value has at most 2 characters",
                "type": "value_error.any_str.max_length",
                "ctx": {"limit_value": 2},
            }
        ]
    else:
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
        response = client.post("/", json=model_json)

        assert response.status_code == 400

        extra = response.json()["extra"]

        if VERSION.startswith("2"):
            # the URL keeps on changing as per the installed pydantic version
            extra[0].pop("url")

        assert extra == expected_errors


def test_default_handling_of_pydantic_errors() -> None:
    @post("/{param:int}")
    def my_route_handler(param: int, data: PydanticPerson) -> None:
        ...

    with create_test_client(my_route_handler) as client:
        response = client.post("/123", json={"first_name": "moishe"})
        extra = response.json().get("extra")
        assert extra is not None
        assert 3 if len(extra) == VERSION.startswith("1") else 4


def test_signature_model_invalid_input() -> None:
    class OtherChild(BaseModel):
        val: List[int]

    class Child(BaseModel):
        val: int
        other_val: int

    class Parent(BaseModel):
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
        if VERSION.startswith("1"):
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
