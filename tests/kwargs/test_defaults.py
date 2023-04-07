from litestar import get
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client


def test_params_default() -> None:
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
