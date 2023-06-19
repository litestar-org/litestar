from docs.examples.application_hooks import before_send_hook

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_application_before_send_hooks() -> None:
    with TestClient(app=before_send_hook.app) as client:
        response = client.get("/test")
        assert response.status_code == HTTP_200_OK
        assert response.headers.get("My Header") == "value injected during send"
