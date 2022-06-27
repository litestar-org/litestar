from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode

import pytest
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from starlite import Parameter, get
from starlite.testing import create_test_client


@pytest.mark.parametrize(
    "params_dict,should_raise",
    [
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas"],
            },
            False,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
            },
            False,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
            },
            True,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas", "Rebok", "Polgat"],
            },
            True,
        ),
        (
            {
                "page": 1,
                "pageSize": 101,
                "brands": ["Nike", "Adidas", "Rebok"],
            },
            True,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": [],
            },
            True,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
                "from_date": datetime.now().timestamp(),
            },
            False,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
                "from_date": datetime.now().timestamp(),
                "to_date": datetime.now().timestamp(),
            },
            False,
        ),
    ],
)
def test_query_params(params_dict: dict, should_raise: bool) -> None:
    test_path = "/test"

    @get(path=test_path)
    def test_method(
        page: int,
        page_size: int = Parameter(query="pageSize", gt=0, le=100),
        brands: List[str] = Parameter(min_items=1, max_items=3),
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> None:
        assert page
        assert page_size
        assert brands
        assert from_date or from_date is None
        assert to_date or to_date is None

    with create_test_client(test_method) as client:
        response = client.get(f"{test_path}?{urlencode(params_dict, doseq=True)}")
        if should_raise:
            assert response.status_code == HTTP_400_BAD_REQUEST
        else:
            assert response.status_code == HTTP_200_OK
