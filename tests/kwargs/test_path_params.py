from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid1, uuid4

import pytest
from pydantic import UUID4

from starlite import MediaType, Starlite, get, post
from starlite.exceptions import ImproperlyConfiguredException
from starlite.params import Parameter
from starlite.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from starlite.testing import create_test_client


@pytest.mark.parametrize(
    "params_dict,should_raise",
    [
        (
            {
                "version": 1.0,
                "service_id": 1,
                "user_id": "abc",
                "order_id": str(uuid4()),
            },
            False,
        ),
        (
            {
                "version": 4.1,
                "service_id": 1,
                "user_id": "abc",
                "order_id": str(uuid4()),
            },
            True,
        ),
        (
            {
                "version": 0.2,
                "service_id": 101,
                "user_id": "abc",
                "order_id": str(uuid4()),
            },
            True,
        ),
        (
            {
                "version": 0.2,
                "service_id": 1,
                "user_id": "abcdefghijklm",
                "order_id": str(uuid4()),
            },
            True,
        ),
        (
            {
                "version": 0.2,
                "service_id": 1,
                "user_id": "abc",
                "order_id": str(uuid1()),
            },
            True,
        ),
    ],
)
def test_path_params(params_dict: dict, should_raise: bool) -> None:
    test_path = "{version:float}/{service_id:int}/{user_id:str}/{order_id:uuid}"

    @get(path=test_path)
    def test_method(
        order_id: UUID4,
        version: float = Parameter(gt=0.1, le=4.0),
        service_id: int = Parameter(gt=0, le=100),
        user_id: str = Parameter(min_length=1, max_length=10),
    ) -> None:
        assert version
        assert service_id
        assert user_id
        assert order_id

    with create_test_client(test_method) as client:
        response = client.get(
            f"{params_dict['version']}/{params_dict['service_id']}/{params_dict['user_id']}/{params_dict['order_id']}"
        )
        if should_raise:
            assert response.status_code == HTTP_400_BAD_REQUEST, response.json()
        else:
            assert response.status_code == HTTP_200_OK, response.json()


@pytest.mark.parametrize(
    "path",
    [
        "/{param}",
        "/{param:foo}",
        "/{param:int:int}",
        "/{:int}",
        "/{param:}",
        "/{  :int}",
        "/{:}",
        "/{::}",
        "/{}",
    ],
)
def test_path_param_validation(path: str) -> None:
    @get(path=path)
    def test_method() -> None:
        raise AssertionError("should not be called")

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[test_method])


def test_duplicate_path_param_validation() -> None:
    @get(path="/{param:int}/foo/{param:int}")
    def test_method() -> None:
        raise AssertionError("should not be called")

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[test_method])


@pytest.mark.parametrize(
    "param_type_name, param_type_class, value",
    [
        ["str", str, "abc"],
        ["int", int, 1],
        ["float", float, 1.01],
        ["uuid", UUID, uuid4()],
        ["decimal", Decimal, Decimal("1.00001")],
        ["date", date, date.today().isoformat()],
        ["datetime", datetime, datetime.now().isoformat()],
        ["timedelta", timedelta, timedelta(days=1).total_seconds()],
        ["path", Path, "/1/2/3/4/some-file.txt"],
        ["path", Path, "1/2/3/4/some-file.txt"],
    ],
)
def test_path_param_type_resolution(param_type_name: str, param_type_class: Any, value: Any) -> None:
    @get("/some/test/path/{test:" + param_type_name + "}")
    def handler(test: param_type_class) -> None:
        if isinstance(test, (date, datetime)):
            assert test.isoformat() == value
        elif isinstance(test, timedelta):
            assert test.total_seconds() == value
        elif isinstance(test, Decimal):
            assert str(test) == str(value)
        elif isinstance(test, Path):
            assert str(test) == str(Path("/1/2/3/4/some-file.txt"))
        else:
            assert test == value

    with create_test_client(handler) as client:
        response = client.get("/some/test/path/" + str(value))
        assert response.status_code == HTTP_200_OK, response.json()


def test_differently_named_path_params_on_same_level() -> None:
    @get("/{name:str}", media_type=MediaType.TEXT)
    def get_greeting(name: str) -> str:
        return f"Hello, {name}!"

    @post("/{title:str}", media_type=MediaType.TEXT)
    def post_greeting(title: str) -> str:
        return f"Hello, {title}!"

    with create_test_client(route_handlers=[get_greeting, post_greeting]) as client:
        response = client.get("/Moishe")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello, Moishe!"
        response = client.post("/Moishe")
        assert response.status_code == HTTP_201_CREATED
        assert response.text == "Hello, Moishe!"
