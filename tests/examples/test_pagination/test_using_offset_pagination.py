from docs.examples.pagination.using_offset_pagination import app

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_using_offset_pagination() -> None:
    with TestClient(app) as client:
        response = client.get("/people", params={"limit": 5, "offset": 0})
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert len(response_data["items"]) == 5
        assert response_data["total"] == 50
        assert response_data["limit"] == 5
        assert response_data["offset"] == 0
