# pyright: reportUnnecessaryTypeIgnoreComment=false

import pydantic as pydantic_v2
import pytest

from litestar import Litestar, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import FromQuery, JSONBody
from litestar.testing import create_test_client


@pytest.mark.parametrize("base_model", [pydantic_v2.BaseModel])
def test_inject_pydantic_model(base_model: type) -> None:
    class Foo(base_model):  # type: ignore[misc]
        bar: FromQuery[str]

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/?bar=baz")
        assert res.status_code == 200
        assert res.json() == {"bar": "baz"}


def test_model_field_from_provider() -> None:
    class Foo(pydantic_v2.BaseModel):
        bar: int

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False), "bar": Provide(lambda: 1, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"bar": 1}


def test_model_field_default() -> None:
    class Foo(pydantic_v2.BaseModel):
        bar: int = 2

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"bar": 2}


def test_model_query_field_default() -> None:
    class Foo(pydantic_v2.BaseModel):
        bar: FromQuery[int] = 2

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"bar": 2}


def test_model_required_field_without_provider_raises() -> None:
    class Foo(pydantic_v2.BaseModel):
        bar: int

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with pytest.raises(ImproperlyConfiguredException, match="Explicit dependency 'bar'"):
        Litestar([handler])


def test_model_body_field() -> None:
    class Foo(pydantic_v2.BaseModel):
        data: JSONBody[dict[str, int]]

    @post("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.post("/", json={"a": 1})
        assert res.status_code == 201
        assert res.json() == {"data": {"a": 1}}


def test_model_marked_dependency_field() -> None:
    class Foo(pydantic_v2.BaseModel):
        bar: NamedDependency[int]

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False), "bar": Provide(lambda: 1, sync_to_thread=False)})
    async def handler(foo: NamedDependency[Foo]) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"bar": 1}
