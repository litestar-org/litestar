from starlite import Provide, Request, create_test_client, get
from starlite.status_codes import HTTP_200_OK


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
            "first": Provide(first_dependency, cache_per_request=True),
            "second": Provide(second_dependency),
        },
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.content == b"7"  # 1 + 1 + 5

        response2 = client.get("/")
        assert response2.status_code == HTTP_200_OK
        assert response2.content == b"9"  # 2 + 2 + 5


def test_explicit_key() -> None:
    @get()
    def route(first: int, request: Request) -> bool:
        return request.state["_dependency_cache"]["override"] == first  # type: ignore[no-any-return]

    with create_test_client(
        route,
        dependencies={
            "first": Provide(lambda: 1, cache_per_request=True, cache_key="override"),
        },
    ) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.content == b"true"
