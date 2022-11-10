from typing import TYPE_CHECKING, List, Optional

import pytest
from hypothesis import given
from hypothesis.strategies import permutations

from starlite import CORSConfig, create_test_client, get, route
from starlite.status_codes import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST

if TYPE_CHECKING:
    from starlite.types import Method


@given(http_methods=permutations(["GET", "POST", "POST", "PATCH", "DELETE", "HEAD"]))
def test_regular_options_request(http_methods: List["Method"]) -> None:
    @route("/", http_method=http_methods)  # type: ignore
    def handler() -> None:
        return None

    with create_test_client(handler) as client:
        response = client.options("/")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.headers.get("Allow") == ", ".join(sorted(set(http_methods + ["OPTIONS"])))


def test_cors_options_request_without_origin_passes() -> None:
    @get("/")
    def handler() -> None:
        return None

    with create_test_client(handler, cors_config=CORSConfig(allow_origins=["http://testserver.local"])) as client:
        response = client.options("/")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.headers.get("Allow") == "GET, OPTIONS"


def test_cors_options_request_with_correct_origin_passes() -> None:
    @get("/")
    def handler() -> None:
        return None

    with create_test_client(handler, cors_config=CORSConfig(allow_origins=["http://testserver.local"])) as client:
        response = client.options("/", headers={"Origin": "http://testserver.local"})
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.headers.get("Access-Control-Allow-Methods") == "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"


def test_cors_options_request_with_wrong_origin_is_blocked() -> None:
    @get("/")
    def handler() -> None:
        return None

    with create_test_client(handler, cors_config=CORSConfig(allow_origins=["http://testserver.local"])) as client:
        response = client.options("/", headers={"Origin": "https://moishe.zuchmir"})
        assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    "allowed_origins, allowed_origin_regex, origin",
    (
        (["http://testserver.local", "https://moishe.zuchmir"], None, "https://moishe.zuchmir"),
        (["http://testserver.local", "https://moishe.zuchmir"], None, "http://testserver.local"),
        (["http://testserver.local", "https://moishe.*"], None, "https://moishe.zuchmir"),
        (["http://testserver.local", "https://moishe.*.abc.com"], None, "https://moishe.zuchmir.abc.com"),
        (["http://testserver.local", "https://moishe.*.*.com"], None, "https://moishe.zuchmir.zzz.com"),
        (["http://testserver.local"], "https://moishe.*.*.com", "https://moishe.zuchmir.zzz.com"),
        ([], "https://moishe.*.*.com", "https://moishe.zuchmir.zzz.com"),
    ),
)
def test_cors_options_request_with_different_domains_matches_regex(
    allowed_origins: List[str], allowed_origin_regex: Optional[str], origin: str
) -> None:
    @get("/")
    def handler() -> None:
        return None

    with create_test_client(
        handler, cors_config=CORSConfig(allow_origins=allowed_origins, allow_origin_regex=allowed_origin_regex)
    ) as client:
        response = client.options("/", headers={"Origin": origin})
        assert response.status_code == HTTP_204_NO_CONTENT
