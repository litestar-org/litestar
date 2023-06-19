from docs.examples.pagination.using_classic_pagination import app

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_using_classic_pagination() -> None:
    with TestClient(app) as client:
        response = client.get("/people", params={"page_size": 5, "current_page": 1})
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert len(response_data["items"]) == 5
        assert response_data["total_pages"] == 10
        assert response_data["page_size"] == 5
        assert response_data["current_page"] == 1
