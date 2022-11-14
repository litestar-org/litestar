from datetime import datetime
from typing import (
    Any,
    Deque,
    Dict,
    FrozenSet,
    List,
    MutableSequence,
    Optional,
    Set,
    Tuple,
    Union,
)
from urllib.parse import urlencode

import pytest

from starlite import Parameter, get
from starlite.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
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
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike"],
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


@pytest.mark.parametrize(
    "expected_type,provided_value,default,expected_response_code",
    [
        (List[int], [1, 2, 3], ..., HTTP_200_OK),
        (List[int], [1], ..., HTTP_200_OK),
        (List[str], ["foo", "bar"], Parameter(min_items=1), HTTP_200_OK),
        (List[str], ["foo", "bar"], Parameter(min_items=3), HTTP_400_BAD_REQUEST),
        (List[int], ["foo", "bar"], ..., HTTP_400_BAD_REQUEST),
        (Tuple[int, str, int], (1, "foo", 2), ..., HTTP_200_OK),
        (Optional[List[str]], [], None, HTTP_200_OK),
        (Any, [1, 2, 3], ..., HTTP_200_OK),
        (Union[int, List[int]], [1, 2, 3], None, HTTP_200_OK),
        (Union[int, List[int]], [1], None, HTTP_200_OK),
        (Deque[int], [1, 2, 3], None, HTTP_200_OK),
        (Set[int], [1, 2, 3], None, HTTP_200_OK),
        (FrozenSet[int], [1, 2, 3], None, HTTP_200_OK),
        (Tuple[int, ...], [1, 2, 3], None, HTTP_200_OK),
        (MutableSequence[int], [1, 2, 3], None, HTTP_200_OK),
    ],
)
def test_query_param_arrays(expected_type: Any, provided_value: Any, default: Any, expected_response_code: int) -> None:
    test_path = "/test"

    @get(test_path)
    def test_method_with_default(param: Any = default) -> None:
        return None

    @get(test_path)
    def test_method_without_default(param: Any) -> None:
        return None

    test_method = test_method_without_default if default is ... else test_method_with_default
    # Set the type annotation of 'param' in a way mypy can deal with
    test_method.fn.value.__annotations__["param"] = expected_type

    with create_test_client(test_method) as client:
        params = urlencode({"param": provided_value}, doseq=True)
        response = client.get(f"{test_path}?{params}")
        assert response.status_code == expected_response_code


def test_query_kwarg() -> None:
    test_path = "/test"

    params = urlencode(
        {
            "a": ["foo", "bar"],
            "b": "qux",
        },
        doseq=True,
    )

    @get(test_path)
    def test_method(a: List[str], b: List[str], query: Dict[str, Union[str, List[str]]]) -> None:
        assert query == {"a": ["foo", "bar"], "b": ["qux"]}

    with create_test_client(test_method) as client:
        response = client.get(f"{test_path}?{params}")
        assert response.status_code == HTTP_200_OK
