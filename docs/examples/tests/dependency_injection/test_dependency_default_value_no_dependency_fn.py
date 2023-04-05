from examples.dependency_injection import dependency_default_value_no_dependency_fn
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_optional_dependency_in_openapi_schema() -> None:
    with TestClient(app=dependency_default_value_no_dependency_fn.app) as client:
        r = client.get("/schema/openapi.json")
    assert r.status_code == HTTP_200_OK
    assert r.json()["paths"]["/"]["get"]["parameters"][0]["name"] == "optional_dependency"
