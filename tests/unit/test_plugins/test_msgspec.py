import msgspec
import pytest

from litestar import Litestar, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import FromQuery, JSONBody
from litestar.testing import create_test_client


def test_inject_msgspec_struct_field_from_provider() -> None:
    class Foo(msgspec.Struct):
        bar: int

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False), "bar": Provide(lambda: 1, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"bar": 1}


def test_inject_msgspec_struct_field_default() -> None:
    class Foo(msgspec.Struct):
        bar: int = 2

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"bar": 2}


def test_inject_msgspec_struct_required_field_without_provider_raises() -> None:
    class Foo(msgspec.Struct):
        bar: int

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with pytest.raises(ImproperlyConfiguredException, match="'bar'"):
        Litestar([handler])


def test_inject_msgspec_struct_required_query_field_missing_from_request() -> None:
    class Foo(msgspec.Struct):
        bar: FromQuery[int]

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 400
        assert res.json()["detail"] == "Missing required query parameter 'bar' for path /"


def test_inject_msgspec_struct_body_field() -> None:
    class Foo(msgspec.Struct):
        data: JSONBody[dict[str, int]]

    @post("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.post("/", json={"a": 1})
        assert res.status_code == 201
        assert res.json() == {"data": {"a": 1}}


def test_inject_msgspec_struct_marked_dependency_field() -> None:
    class Foo(msgspec.Struct):
        bar: NamedDependency[int]

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False), "bar": Provide(lambda: 1, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"bar": 1}
