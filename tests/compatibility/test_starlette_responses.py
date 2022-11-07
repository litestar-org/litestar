from typing import TYPE_CHECKING

from starlette.responses import JSONResponse

from starlite import create_test_client, get
from starlite.status_codes import HTTP_200_OK

if TYPE_CHECKING:
    from starlite.types import ASGIApp


def test_starlette_json_response() -> None:
    @get("/starlette-json-response")
    def get_json_response() -> "ASGIApp":
        return JSONResponse(content={"hello": "world"})  # type: ignore

    with create_test_client(get_json_response) as client:
        response = client.get("/starlette-json-response")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"hello": "world"}
