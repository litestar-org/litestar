import pytest
from docs.examples.pagination.using_offset_pagination_with_sqlalchemy import app

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


# 'advanced_alchemy.extensions.litestar' calls its own deprecated 'set_async_context' from
# 'provide_session' on every request, which 'filterwarnings = error' would turn into a 500.
@pytest.mark.filterwarnings("ignore:Call to deprecated function 'set_async_context':DeprecationWarning")
def test_using_offset_pagination_with_sqlalchemy() -> None:
    with TestClient(app) as client:
        response = client.get("/people", params={"limit": 5, "offset": 0})
        assert response.status_code == HTTP_200_OK
        response_data = response.json()
        assert len(response_data["items"]) == 5
        assert response_data["total"] == 50
        assert response_data["limit"] == 5
        assert response_data["offset"] == 0
