from litestar import get
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import create_test_client


def test_root_path_param_resolution() -> None:
    # https://github.com/litestar-org/litestar/issues/1830
    @get("/{name:str}")
    async def hello_world(name: str) -> str:
        return f"Hello, {name}!"

    with create_test_client(hello_world) as client:
        response = client.get("/jon")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello, jon!"

        response = client.get("/jon/bon")
        assert response.status_code == HTTP_404_NOT_FOUND

        response = client.get("/jon/bon/jovi")
        assert response.status_code == HTTP_404_NOT_FOUND
