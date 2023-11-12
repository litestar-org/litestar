from attrs import define

from litestar import post
from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import create_test_client


def test_parse_attrs_data_in_signature() -> None:
    @define(slots=True, frozen=True)
    class AttrsUser:
        name: str
        email: str

    @post("/")
    async def attrs_data(data: AttrsUser) -> AttrsUser:
        return data

    with create_test_client([attrs_data]) as client:
        response = client.post("/", json={"name": "foo", "email": "e@example.com"})
        assert response.status_code == HTTP_201_CREATED
        assert response.json().get("name") == "foo"
        assert response.json().get("email") == "e@example.com"
