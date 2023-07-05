from docs.examples.dependency_injection import dependency_with_dependency_fn_and_default

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_optional_dependency_not_in_openapi_schema() -> None:
    with TestClient(app=dependency_with_dependency_fn_and_default.app) as client:
        r = client.get("/schema/openapi.json")
    assert r.status_code == HTTP_200_OK
    assert r.json()["paths"]["/"]["get"].get("parameters") is None
