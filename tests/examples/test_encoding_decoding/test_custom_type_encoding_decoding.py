from docs.examples.encoding_decoding.custom_type_encoding_decoding import app

from litestar.status_codes import HTTP_201_CREATED
from litestar.testing import TestClient


def test_custom_type_encoding_decoding_works() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/asset",
            json={
                "user": "TenantA_Somebody",
                "name": "Some Asset",
            },
        )

        assert response.status_code == HTTP_201_CREATED
