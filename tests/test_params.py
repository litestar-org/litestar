from typing import Optional

from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from starlite import Header, create_test_client, get


def test_header_params_key():
    test_path = "/test"

    request_headers = {
        "application-type": "web",
        "site": "www.example.com",
        "user-agent": "some-thing",
        "accept": "*/*",
        "special-header": "123",
    }

    @get(path=test_path)
    def test_method(special_header: str = Header("special-header")):
        assert special_header == request_headers["special-header"]

    with create_test_client(test_method) as client:
        response = client.get(test_path, headers=request_headers)
        assert response.status_code == HTTP_200_OK


def test_header_params_allow_none():
    test_path = "/test"

    @get(path=test_path)
    def test_method(special_header: Optional[str] = Header("special-header")):
        assert special_header is None

    with create_test_client(test_method) as client:
        response = client.get(test_path)
        assert response.status_code == HTTP_200_OK


def test_header_params_validation():
    test_path = "/test"

    @get(path=test_path)
    def test_method(special_header: str = Header("special-header")):
        return special_header

    with create_test_client(test_method) as client:
        response = client.get(test_path)
        assert response.status_code == HTTP_400_BAD_REQUEST
