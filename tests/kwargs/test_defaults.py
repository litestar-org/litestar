from starlette.status import HTTP_200_OK

from starlite import Parameter, create_test_client, get


def test_params_default():
    test_path = "/test"

    @get(path=test_path)
    def test_method(
        page_size: int = Parameter(query="pageSize", gt=0, le=100, default=10),
    ) -> None:
        assert page_size

    with create_test_client(test_method) as client:
        response = client.get(f"{test_path}?pageSize=10")
        assert response.status_code == HTTP_200_OK

        response = client.get(f"{test_path}")
        assert response.status_code == HTTP_200_OK
