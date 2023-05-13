from attrs import define
from pydantic import BaseModel

from litestar import post
from litestar.testing import create_test_client


def test_signature_model_validation() -> None:
    @define(slots=True, frozen=True)
    class AttrsUser:
        name: str

    class PydanticUser(BaseModel):
        name: str

    @post("/attrs")
    async def attrs_data(data: AttrsUser) -> bool:
        return isinstance(data, AttrsUser)

    @post("/pydantic")
    async def pydantic_data(data: PydanticUser) -> bool:
        return isinstance(data, PydanticUser)

    with create_test_client([attrs_data, pydantic_data]) as client:
        assert client.post("/pydantic", json={"name": "foo"}).json() is True
        assert client.post("/attrs", json={"name": "foo"}).json() is True
