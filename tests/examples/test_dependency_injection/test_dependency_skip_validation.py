from docs.examples.dependency_injection import dependency_skip_validation

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_route_skips_validation() -> None:
    with TestClient(app=dependency_skip_validation.app) as client:
        r = client.get("/")
    assert r.status_code == HTTP_200_OK
