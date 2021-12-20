from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode

import pytest
from pydantic import conint, conlist
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from starlite import Header, create_test_client, get


@pytest.mark.parametrize(
    "query,should_raise",
    [
        (
            {
                "page": 1,
                "page_size": 1,
                "brands": ["Nike", "Adidas"],
            },
            False,
        ),
        (
            {
                "page": 1,
                "page_size": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
            },
            False,
        ),
        (
            {
                "page": 1,
                "page_size": 1,
            },
            True,
        ),
        (
            {
                "page": 1,
                "page_size": 1,
                "brands": ["Nike", "Adidas", "Rebok", "Polgat"],
            },
            True,
        ),
        (
            {
                "page": 1,
                "page_size": 101,
                "brands": ["Nike", "Adidas", "Rebok"],
            },
            True,
        ),
        (
            {
                "page": 1,
                "page_size": 1,
                "brands": [],
            },
            True,
        ),
        (
            {
                "page": 1,
                "page_size": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
                "from_date": datetime.now().timestamp(),
            },
            False,
        ),
        (
            {
                "page": 1,
                "page_size": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
                "from_date": datetime.now().timestamp(),
                "to_date": datetime.now().timestamp(),
            },
            False,
        ),
    ],
)
def test_query_params(query: dict, should_raise: bool):
    test_path = "/test"

    @get(path=test_path)
    def test_method(
        page: int,
        page_size: int = conint(gt=0, le=100),
        brands: List[str] = conlist(str, min_items=1, max_items=3),
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        assert page
        assert page_size
        assert brands
        assert from_date or from_date is None
        assert to_date or to_date is None

    with create_test_client(test_method) as client:
        response = client.get(f"{test_path}?{urlencode(query, doseq=True)}")
        if should_raise:
            assert response.status_code == HTTP_400_BAD_REQUEST
        else:
            assert response.status_code == HTTP_200_OK


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
    def test_method(special_header: Optional[str] = Header("special-header", required=False)):
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
