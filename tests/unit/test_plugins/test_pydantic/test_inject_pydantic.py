from litestar import get
from litestar.di import Provide
from litestar.testing import create_test_client


def test_inject_pydantic_model(base_model: type) -> None:
    class Foo(base_model):  # type: ignore[misc]
        bar: str

    @get("/", dependencies={"foo": Provide(Foo, sync_to_thread=False)})
    async def handler(foo: Foo) -> Foo:
        return foo

    with create_test_client([handler]) as client:
        res = client.get("/?bar=baz")
        assert res.status_code == 200
        assert res.json() == {"bar": "baz"}
