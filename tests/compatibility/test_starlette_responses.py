from starlette.responses import JSONResponse

from litestar import get
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client


def test_starlette_json_response() -> None:
    @get("/starlette-json-response")
    def get_json_response() -> JSONResponse:
        return JSONResponse(content={"hello": "world"})

    with create_test_client(get_json_response) as client:
        response = client.get("/starlette-json-response")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"hello": "world"}
