from starlite import get
from starlite.di import Provide
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client


def test_caching_per_request() -> None:
    value = 1

    def first_dependency() -> int:
        nonlocal value
        tmp = value
        value += 1
        return tmp  # noqa: R504

    def second_dependency(first: int) -> int:
        return first + 5

    @get()
    def route(first: int, second: int) -> int:
        return first + second

    with create_test_client(
        route,
        dependencies={
            "first": Provide(first_dependency),
            "second": Provide(second_dependency),
        },
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.content == b"7"  # 1 + 1 + 5

        response2 = client.get("/")
        assert response2.status_code == HTTP_200_OK
        assert response2.content == b"9"  # 2 + 2 + 5
