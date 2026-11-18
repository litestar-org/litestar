# pyright: reportUnnecessaryTypeIgnoreComment=false

from dataclasses import dataclass
from typing import Annotated, Generic, Optional, TypeVar

import pytest
from attr import define
from typing_extensions import TypedDict

from litestar import Litestar, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import (
    CookieParameter,
    FromHeader,
    FromQuery,
    HeaderParameter,
    JSONBody,
    PathParameter,
    QueryParameter,
)
from litestar.status_codes import HTTP_400_BAD_REQUEST
from litestar.testing import create_test_client


def test_parameter_without_annotation_raises() -> None:
    @get()
    def my_fn(typed: FromQuery[int], untyped) -> None:  # type: ignore[no-untyped-def]
        pass

    with pytest.raises(ImproperlyConfiguredException, match="'untyped' does not have a type annotation"):
        Litestar([my_fn])


def test_dependency_value_is_not_validated() -> None:
    dependencies = {"dep": Provide(lambda: "thirteen", sync_to_thread=False)}
    received: list[object] = []

    @get("/")
    def test(
        dep: NamedDependency[int], param: FromQuery[int], optional_dep: NamedDependency[Optional[int]] = None
    ) -> None:
        received.append(dep)

    with create_test_client(
        route_handlers=[test],
        dependencies=dependencies,
        debug=False,
    ) as client:
        response = client.get("/?param=13")

    assert response.status_code == 200
    assert received == ["thirteen"]


def test_validation_failure_raises_400() -> None:
    dependencies = {"dep": Provide(lambda: 13, sync_to_thread=False)}

    @get("/")
    def test(
        dep: NamedDependency[int], param: FromQuery[int], optional_dep: NamedDependency[Optional[int]] = None
    ) -> None: ...

    with create_test_client(route_handlers=[test], dependencies=dependencies) as client:
        response = client.get("/?param=thirteen")

    assert response.json() == {
        "detail": "Validation failed for GET /?param=thirteen",
        "extra": [{"key": "param", "message": "Expected `int`, got `str`", "source": "query"}],
        "status_code": 400,
    }


def test_invalid_path_parameter() -> None:
    @get("/{param:int}")
    def test(param: Annotated[int, PathParameter(le=10)]) -> None: ...

    with create_test_client(route_handlers=[test]) as client:
        response = client.get("/11")

    assert response.json() == {
        "detail": "Validation failed for GET /11",
        "extra": [{"key": "param", "message": "Expected `int` <= 10", "source": "path"}],
        "status_code": 400,
    }


def test_invalid_marked_parameter_named_like_path_parameter_reports_marked_source() -> None:
    @get("/{param:str}")
    def test(param: FromHeader[int]) -> None: ...

    with create_test_client(route_handlers=[test]) as client:
        response = client.get("/thirteen", headers={"param": "thirteen"})

    assert response.json() == {
        "detail": "Validation failed for GET /thirteen",
        "extra": [{"key": "param", "message": "Expected `int`, got `str`", "source": "header"}],
        "status_code": 400,
    }


def test_validation_error_exception_key() -> None:
    from dataclasses import dataclass

    @dataclass
    class OtherChild:
        val: list[int]

    @dataclass
    class Child:
        val: int
        other_val: int

    @dataclass
    class Parent:
        child: Child
        other_child: OtherChild

    @post("/")
    def handler(data: JSONBody[Parent]) -> None:
        pass

    with create_test_client([handler]) as client:
        response = client.post("/", json={"child": {}, "other_child": {}})

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["extra"][0]["key"] == "child"


def test_invalid_input_attrs() -> None:
    @define
    class OtherChild:
        val: list[int]

    @define
    class Child:
        val: int
        other_val: int

    @define
    class Parent:
        child: Child
        other_child: OtherChild

    @post("/")
    def test(
        data: JSONBody[Parent],
        int_param: FromQuery[int],
        int_header: Annotated[int, HeaderParameter(name="X-SOME-INT")],
        int_cookie: Annotated[int, CookieParameter(name="int-cookie")],
    ) -> None: ...

    with create_test_client(route_handlers=[test]) as client:
        client.cookies.update({"int-cookie": "cookie"})
        response = client.post(
            "/",
            json={"child": {"val": "a", "other_val": "b"}, "other_child": {"val": [1, "c"]}},
            params={"int_param": "param"},
            headers={"X-SOME-INT": "header"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        data = response.json()

        assert data
        assert data["extra"] == [
            {"message": "Expected `int`, got `str`", "key": "child.val", "source": "body"},
            {"message": "Expected `int`, got `str`", "key": "int_param", "source": "query"},
            {"message": "Expected `int`, got `str`", "key": "X-SOME-INT", "source": "header"},
            {"message": "Expected `int`, got `str`", "key": "int-cookie", "source": "cookie"},
        ]


def test_invalid_input_dataclass() -> None:
    @dataclass
    class OtherChild:
        val: list[int]

    @dataclass
    class Child:
        val: int
        other_val: int

    @dataclass
    class Parent:
        child: Child
        other_child: OtherChild

    @post("/")
    def test(
        data: JSONBody[Parent],
        int_param: FromQuery[int],
        length_param: Annotated[str, QueryParameter(min_length=2)],
        int_header: Annotated[int, HeaderParameter(name="X-SOME-INT")],
        int_cookie: Annotated[int, CookieParameter(name="int-cookie")],
    ) -> None: ...

    with create_test_client(route_handlers=[test]) as client:
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
        assert data["extra"] == [
            {"message": "Expected `int`, got `str`", "key": "child.val", "source": "body"},
            {"message": "Expected `int`, got `str`", "key": "int_param", "source": "query"},
            {"message": "Expected `str` of length >= 2", "key": "length_param", "source": "query"},
            {"message": "Expected `int`, got `str`", "key": "X-SOME-INT", "source": "header"},
            {"message": "Expected `int`, got `str`", "key": "int-cookie", "source": "cookie"},
        ]


def test_invalid_input_typed_dict() -> None:
    class OtherChild(TypedDict):
        val: list[int]

    class Child(TypedDict):
        val: int
        other_val: int

    class Parent(TypedDict):
        child: Child
        other_child: OtherChild

    @post("/")
    def test(
        data: JSONBody[Parent],
        int_param: FromQuery[int],
        length_param: Annotated[str, QueryParameter(min_length=2)],
        int_header: Annotated[int, HeaderParameter(name="X-SOME-INT")],
        int_cookie: Annotated[int, CookieParameter(name="int-cookie")],
    ) -> None: ...

    with create_test_client(route_handlers=[test]) as client:
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
        assert data["extra"] == [
            {"message": "Expected `int`, got `str`", "key": "child.val", "source": "body"},
            {"message": "Expected `int`, got `str`", "key": "int_param", "source": "query"},
            {"message": "Expected `str` of length >= 2", "key": "length_param", "source": "query"},
            {"message": "Expected `int`, got `str`", "key": "X-SOME-INT", "source": "header"},
            {"message": "Expected `int`, got `str`", "key": "int-cookie", "source": "cookie"},
        ]


def test_constraint_violations_of_parameters_reported_together() -> None:
    @get("/")
    def handler(a: Annotated[int, QueryParameter(gt=5)], b: Annotated[int, QueryParameter(lt=5)]) -> None:
        pass

    with create_test_client([handler]) as client:
        response = client.get("/?a=0&b=9")

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["extra"] == [
        {"message": "Expected `int` >= 6", "key": "a", "source": "query"},
        {"message": "Expected `int` <= 4", "key": "b", "source": "query"},
    ]


def test_validate_subscribed_generics() -> None:
    T = TypeVar("T")

    class Foo(Generic[T]):
        def __init__(self, value: str) -> None:
            self.value = value

    @get("/", type_decoders=[(lambda t: t == Foo[str], lambda _, v: Foo(v))])
    async def something(foo: FromQuery[Foo[str]]) -> str:
        return foo.value

    with create_test_client([something]) as client:
        response = client.get("/?foo=x")

    assert response.status_code == 200
    assert response.text == "x"


def test_separate_model_namespace() -> None:
    # https://github.com/litestar-org/litestar/issues/3593

    async def provide_connection() -> str:
        return "connection"

    @get("/connection", dependencies={"connection": provide_connection})
    async def get_connection(connection: NamedDependency[str]) -> str:
        return connection

    async def provide_deserializer() -> str:
        return "deserializer"

    @get("/deserializer", dependencies={"deserializer": provide_deserializer})
    async def get_deserializer(deserializer: NamedDependency[int]) -> str:
        return deserializer  # type: ignore[return-value]

    with create_test_client([get_connection, get_deserializer], raise_server_exceptions=True, debug=True) as client:
        assert client.get("/connection").text == "connection"
        assert client.get("/deserializer").text == "deserializer"
