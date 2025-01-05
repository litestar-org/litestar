from litestar.testing import TestClient


def test_app() -> None:
    from docs.examples.security.jwt.verify_issuer_audience import app, jwt_auth

    valid_token = jwt_auth.create_token(
        "foo",
        token_audience=jwt_auth.accepted_audiences[0],
        token_issuer=jwt_auth.accepted_issuers[0],
    )
    invalid_token = jwt_auth.create_token("foo")

    with TestClient(app) as client:
        response = client.get("/", headers={"Authorization": jwt_auth.format_auth_header(valid_token)})
        assert response.status_code == 200
        response = client.get("/", headers={"Authorization": jwt_auth.format_auth_header(invalid_token)})
        assert response.status_code == 401
