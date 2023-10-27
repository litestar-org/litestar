import pydantic

from litestar import get
from litestar.testing import create_test_client


def test_app_with_v1_and_v2_models() -> None:
    class ModelV1(pydantic.v1.BaseModel):  # pyright: ignore
        foo: str

    class ModelV2(pydantic.BaseModel):
        foo: str

    @get("/v1")
    def handler_v1() -> ModelV1:
        return ModelV1(foo="bar")

    @get("/v2")
    def handler_v2() -> ModelV2:
        return ModelV2(foo="bar")

    with create_test_client([handler_v1, handler_v2]) as client:
        assert client.get("/v1").json() == {"foo": "bar"}
        assert client.get("/v2").json() == {"foo": "bar"}
