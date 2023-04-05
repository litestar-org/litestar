from typing import TYPE_CHECKING

import pytest

from examples.routing import mount_custom_app, mounting_starlette_app
from starlite.status_codes import HTTP_200_OK
from starlite.testing import TestClient

if TYPE_CHECKING:
    from starlite import Starlite


@pytest.mark.parametrize(
    "app",
    (
        mount_custom_app.app,
        mounting_starlette_app.app,
    ),
)
def test_mounting_asgi_app_example(app: "Starlite") -> None:
    with TestClient(app) as client:
        response = client.get("/some/sub-path")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"forwarded_path": "/"}

        response = client.get("/some/sub-path/abc")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"forwarded_path": "/abc/"}

        response = client.get("/some/sub-path/123/another/sub-path")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"forwarded_path": "/123/another/sub-path/"}
